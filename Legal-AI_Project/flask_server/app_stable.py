import os
os.environ['TOKENIZERS_PARALLELISM'] = 'false'  # Disable tokenizer parallelism

from flask import Flask, request, jsonify
from textblob import TextBlob
from paraphrase import paraphrase
from predict_simple import run_prediction
from io import BytesIO
import json
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
        return [
            "What is the contract name?",
            "Who are the parties involved?",
            "What is the agreement date?",
            "What is the governing law?",
            "What are the termination conditions?"
        ]

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

def extract_text_from_file(content, filename):
    """Extract text from file content"""
    try:
        # Try text decoding first
        encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']
        for encoding in encodings:
            try:
                text = content.decode(encoding)
                if text.strip():
                    return text.strip()
            except (UnicodeDecodeError, UnicodeError):
                continue
        
        # Try PDF if text decoding fails
        if PdfFileReader and filename and filename.lower().endswith('.pdf'):
            try:
                pdf = PdfFileReader(BytesIO(content))
                text = ""
                for page in range(min(pdf.getNumPages(), 20)):  # Limit pages
                    text += pdf.getPage(page).extractText() + "\n"
                if text.strip():
                    return text.strip()
            except Exception as e:
                print(f"PDF processing error: {str(e)}")
        
        return None
    except Exception as e:
        print(f"Text extraction error: {str(e)}")
        return None

@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
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

        if not file:
            return jsonify({"error": "No file provided"}), 400
        
        if not question:
            return jsonify({"error": "No question provided"}), 400

        # Extract text
        content = file.read()
        paragraph = extract_text_from_file(content, file.filename)
        
        if not paragraph:
            return jsonify({"error": "Could not extract text from file"}), 400

        print(f'Processing question: {question}')
        print(f'Document length: {len(paragraph)} characters')
        
        # Get predictions
        predictions = run_prediction([question], paragraph, 'deepset/roberta-base-squad2')
        
        # Process results
        answer_text = predictions.get('0', '').strip()
        
        if answer_text:
            result = [{
                "answer": answer_text,
                "probability": "High",
                "analyse": getContractAnalysis(answer_text)
            }]
        else:
            result = [{
                "answer": "No answer found in document",
                "probability": "0%",
                "analyse": "Neutral"
            }]
                
        return jsonify(result)
        
    except Exception as e:
        print(f"Error processing request: {str(e)}")
        import traceback
        traceback.print_exc()
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

if __name__ == '__main__':
    print("Starting Legal AI Flask Server...")
    print("Server will be available at: http://127.0.0.1:5000")
    app.run(debug=False, host='127.0.0.1', port=5000, threaded=True)