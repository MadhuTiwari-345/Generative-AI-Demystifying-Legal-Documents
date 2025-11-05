from flask import Flask, request, jsonify
from textblob import TextBlob
from paraphrase import paraphrase
from predict_simple import run_prediction
from io import BytesIO
import json
import os
import time
from functools import lru_cache
from flask_cors import CORS
try:
    from PyPDF4 import PdfFileReader
except ImportError:
    print("Warning: PyPDF4 not installed. PDF processing will not be available.")
    PdfFileReader = None

app = Flask(__name__)
CORS(app)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Cache for questions
_questions_cache = None

@lru_cache(maxsize=1)
def load_questions_short():
    try:
        with open('data/questions_short.txt', encoding="utf8") as f:
            return [line.strip() for line in f.readlines() if line.strip()]
    except FileNotFoundError:
        print("Warning: questions_short.txt not found")
        return []

@lru_cache(maxsize=128)
def getContractAnalysis(selected_response):
    if not selected_response or selected_response.strip() == "":
        return "Neutral"
    
    try:
        blob = TextBlob(selected_response)
        polarity = blob.sentiment.polarity
        
        if polarity > 0.1:
            return "Positive"
        elif polarity < -0.1:
            return "Negative"
        else:
            return "Neutral"
    except Exception as e:
        print(f"Sentiment analysis error: {str(e)}")
        return "Neutral"

def is_readable_text(text):
    """Check if text contains readable English characters"""
    if not text or len(text.strip()) == 0:
        return False
    
    # Count readable ASCII characters
    readable_chars = sum(1 for c in text if c.isprintable() and ord(c) < 128)
    total_chars = len(text)
    
    # If less than 70% are readable ASCII, it's probably corrupted
    if total_chars == 0:
        return False
    
    readable_ratio = readable_chars / total_chars
    return readable_ratio > 0.7

def clean_text_output(text):
    """Clean and validate text output"""
    if not text:
        return ""
    
    # Remove non-printable characters
    cleaned = ''.join(c for c in text if c.isprintable())
    
    # Remove excessive whitespace
    cleaned = ' '.join(cleaned.split())
    
    # Check if the result is readable
    if not is_readable_text(cleaned):
        return ""
    
    return cleaned.strip()

def extract_text_from_file(content, filename):
    """Extract text from file content based on file type"""
    paragraph = None
    
    # Try text decoding first with proper encoding detection
    encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252', 'iso-8859-1']
    for encoding in encodings:
        try:
            decoded_text = content.decode(encoding)
            cleaned_text = clean_text_output(decoded_text)
            
            if cleaned_text and is_readable_text(cleaned_text):
                print(f"Successfully decoded with {encoding}")
                return cleaned_text
        except (UnicodeDecodeError, UnicodeError):
            continue
    
    # Try PDF if text decoding fails
    if paragraph is None and PdfFileReader and filename and filename.lower().endswith('.pdf'):
        try:
            pdf = PdfFileReader(BytesIO(content))
            paragraph = ""
            for page in range(min(pdf.getNumPages(), 50)):  # Limit to 50 pages
                page_text = pdf.getPage(page).extractText()
                cleaned_page = clean_text_output(page_text)
                if cleaned_page:
                    paragraph += cleaned_page + "\n"
            
            if paragraph.strip() and is_readable_text(paragraph):
                return paragraph
        except Exception as e:
            print(f"PDF processing error: {str(e)}")
    
    # If all else fails, try to extract any readable text
    try:
        # Force decode as latin-1 (never fails) then clean
        raw_text = content.decode('latin-1', errors='ignore')
        cleaned = clean_text_output(raw_text)
        if cleaned and is_readable_text(cleaned):
            print("Used fallback latin-1 decoding")
            return cleaned
    except Exception as e:
        print(f"Fallback decoding error: {str(e)}")
    
    return None

def process_predictions(predictions):
    """Process ML model predictions into response format"""
    answer = []
    
    print(f"Processing predictions: {predictions}")
    
    # Check if we have any predictions at all
    if not predictions:
        print("No predictions returned from model")
        return None
    
    try:
        # First, try direct predictions (this is the main result)
        main_answer = predictions.get('0', '').strip()
        if main_answer:
            # Clean and validate the main answer
            cleaned_answer = clean_text_output(main_answer)
            if cleaned_answer and is_readable_text(cleaned_answer):
                print(f"Found main prediction: {cleaned_answer}")
                answer.append({
                    "answer": cleaned_answer,
                    "probability": "Main",
                    "analyse": getContractAnalysis(cleaned_answer)
                })
            else:
                print(f"Main prediction not readable: {repr(main_answer)}")
        
        # Then try to load nbest.json for additional results
        if os.path.exists("nbest.json"):
            print("Loading nbest.json for additional results")
            with open("nbest.json", encoding="utf8") as jf:
                data = json.load(jf)
                results = data.get('0', [])
                
                # Add top alternatives (skip the first one if it's the same as main)
                for i, result in enumerate(results[:3]):
                    text = result.get('text', '').strip()
                    probability = result.get('probability', 0)
                    
                    # Clean and validate the text
                    cleaned_text = clean_text_output(text)
                    
                    # Skip empty answers, unreadable text, and duplicates
                    if not cleaned_text or not is_readable_text(cleaned_text) or cleaned_text == main_answer:
                        continue
                        
                    # Only include alternatives with reasonable probability
                    if probability > 0.05:  # 5% threshold for alternatives
                        answer.append({
                            "answer": cleaned_text,
                            "probability": f"{round(probability*100, 1)}%",
                            "analyse": getContractAnalysis(cleaned_text)
                        })
                        print(f"Added alternative: {cleaned_text} with probability {probability}")
                
                # If no main answer but we have nbest results, use the best readable one
                if not main_answer and results:
                    for result in results:
                        text = result.get('text', '').strip()
                        probability = result.get('probability', 0)
                        
                        cleaned_text = clean_text_output(text)
                        
                        if cleaned_text and is_readable_text(cleaned_text) and probability > 0.01:
                            answer.append({
                                "answer": cleaned_text,
                                "probability": f"{round(probability*100, 1)}%",
                                "analyse": getContractAnalysis(cleaned_text)
                            })
                            print(f"Used best readable nbest result: {cleaned_text}")
                            break
                
    except Exception as e:
        print(f"Error processing predictions: {str(e)}")
        import traceback
        traceback.print_exc()
        return None
    
    print(f"Final processed answers: {answer}")
    return answer if answer else None

@app.route('/health')
def health_check():
    """Simple health check endpoint"""
    return jsonify({
        "status": "healthy",
        "model_loaded": True,
        "timestamp": time.time()
    })

@app.route('/questionsshort')
def getQuestionsShort():
    global _questions_cache
    if _questions_cache is None:
        _questions_cache = load_questions_short()
    return jsonify(_questions_cache)

@app.route('/contracts/', methods=["POST"])
def getContractResponse():
    try:
        file = request.files.get("file")
        question = request.form.get('question')

        if not file or not question:
            return jsonify({"error": "Missing file or question"}), 400

        content = file.read()
        paragraph = extract_text_from_file(content, file.filename)
        
        if not paragraph:
            return jsonify({"error": "Could not extract readable text from file"}), 400

        print('Getting predictions...')
        predictions = run_prediction([question], paragraph, 'marshmellow77/roberta-base-cuad', n_best_size=5)
        
        answer = process_predictions(predictions)
        if not answer:
            answer = [{
                "answer": 'No answer found in document',
                "probability": "0%",
                "analyse": "Neutral"
            }]
                
        return jsonify(answer)
        
    except Exception as e:
        print(f"Error processing request: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/contracts/paraphrase/<path:selected_response>', methods=['GET'])
def getContractParaphrase(selected_response):
    if not selected_response or selected_response.strip() == "":
        return jsonify({"error": "No text to paraphrase"}), 400
    
    try:
        print('Getting paraphrases...')
        paraphrases = paraphrase(selected_response)
        return jsonify(paraphrases)
    except Exception as e:
        print(f"Paraphrase error: {str(e)}")
        return jsonify({"error": "Error generating paraphrases"}), 500

@app.route('/get_response', methods=['POST'])
def get_response():
    try:
        question = request.form.get('selected_response')
        if not question:
            return jsonify({"error": "Missing question"}), 400
            
        if os.path.exists('responses.json'):
            with open('responses.json', 'r') as file:
                responses = json.load(file)
                for response in responses:
                    if response.get('question') == question:
                        return jsonify({"answer": response.get('answer', "")})
        
        return jsonify({"error": "Response not found"}), 404
    except Exception as e:
        print(f"Error in get_response: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    app.run(debug=True)