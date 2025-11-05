import os
import json
import time
import re
from io import BytesIO
from flask import Flask, request, jsonify
from flask_cors import CORS
from textblob import TextBlob
import torch
from transformers import AutoTokenizer, AutoModelForQuestionAnswering, pipeline
import fitz  # PyMuPDF
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

class OptimizedLegalQA:
    def __init__(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.qa_pipeline = None
        self.paraphrase_pipeline = None
        self.questions_cache = None
        self._load_models()
        
    def _load_models(self):
        """Load and cache ML models"""
        try:
            logger.info(f"Loading models on {self.device}")
            
            # Load QA model - using a more efficient approach
            self.qa_pipeline = pipeline(
                "question-answering",
                model="deepset/roberta-base-squad2",
                tokenizer="deepset/roberta-base-squad2",
                device=0 if torch.cuda.is_available() else -1,
                return_all_scores=True
            )
            
            # Load paraphrase model
            self.paraphrase_pipeline = pipeline(
                "text2text-generation",
                model="humarin/chatgpt_paraphraser_on_T5_base",
                device=0 if torch.cuda.is_available() else -1
            )
            
            logger.info("Models loaded successfully")
        except Exception as e:
            logger.error(f"Error loading models: {str(e)}")
            
    def extract_text_from_file(self, file_content, filename):
        """Enhanced text extraction with PyMuPDF"""
        try:
            # Try PDF first
            if filename.lower().endswith('.pdf'):
                return self._extract_from_pdf(file_content)
            
            # Try text files with multiple encodings
            encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
            for encoding in encodings:
                try:
                    text = file_content.decode(encoding)
                    return self._clean_text(text)
                except UnicodeDecodeError:
                    continue
                    
            return None
        except Exception as e:
            logger.error(f"Text extraction error: {str(e)}")
            return None
    
    def _extract_from_pdf(self, file_content):
        """Extract text from PDF using PyMuPDF"""
        try:
            doc = fitz.open(stream=file_content, filetype="pdf")
            text = ""
            
            for page_num in range(doc.page_count):
                page = doc[page_num]
                # Extract text with layout preservation
                text += page.get_text("text")
                
            doc.close()
            return self._clean_text(text) if text.strip() else None
        except Exception as e:
            logger.error(f"PDF extraction error: {str(e)}")
            return None
    
    def _clean_text(self, text):
        """Clean and normalize extracted text"""
        if not text:
            return None
            
        # Remove excessive whitespace and normalize
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'\n+', '\n', text)
        text = text.strip()
        
        # Remove common PDF artifacts
        text = re.sub(r'[^\w\s\.\,\;\:\!\?\-\(\)\[\]\{\}\"\'\/\@\#\$\%\&\*\+\=\<\>\|\\\~\`]', '', text)
        
        return text if len(text) > 50 else None
    
    def predict_answer(self, question, context, max_length=512):
        """Optimized answer prediction"""
        try:
            if not self.qa_pipeline:
                return None
                
            # Truncate context intelligently
            if len(context) > max_length * 4:
                # Try to find relevant sections
                sentences = context.split('.')
                relevant_context = ""
                question_words = set(question.lower().split())
                
                for sentence in sentences:
                    sentence_words = set(sentence.lower().split())
                    if question_words.intersection(sentence_words):
                        relevant_context += sentence + ". "
                        if len(relevant_context) > max_length * 3:
                            break
                
                context = relevant_context if relevant_context else context[:max_length * 4]
            
            result = self.qa_pipeline(question=question, context=context)
            
            # Handle multiple answers if available
            if isinstance(result, list):
                return [{
                    "answer": r.get("answer", ""),
                    "confidence": round(r.get("score", 0) * 100, 1),
                    "start": r.get("start", 0),
                    "end": r.get("end", 0)
                } for r in result[:5]]
            else:
                return [{
                    "answer": result.get("answer", ""),
                    "confidence": round(result.get("score", 0) * 100, 1),
                    "start": result.get("start", 0),
                    "end": result.get("end", 0)
                }]
                
        except Exception as e:
            logger.error(f"Prediction error: {str(e)}")
            return None
    
    def analyze_sentiment(self, text):
        """Analyze sentiment of the answer"""
        try:
            if not text or text.strip() == "":
                return "Neutral"
            
            blob = TextBlob(text)
            polarity = blob.sentiment.polarity
            
            if polarity > 0.1:
                return "Positive"
            elif polarity < -0.1:
                return "Negative"
            else:
                return "Neutral"
        except:
            return "Neutral"
    
    def generate_paraphrases(self, text, num_return=3):
        """Generate paraphrases for better understanding"""
        try:
            if not self.paraphrase_pipeline or not text:
                return [text] if text else ["No text to paraphrase"]
            
            input_text = f"paraphrase: {text}"
            results = self.paraphrase_pipeline(
                input_text,
                max_length=150,
                num_return_sequences=num_return,
                temperature=0.7,
                do_sample=True
            )
            
            return [r['generated_text'] for r in results]
        except Exception as e:
            logger.error(f"Paraphrase error: {str(e)}")
            return [text] if text else ["Error generating paraphrases"]

# Initialize the optimized QA system
qa_system = OptimizedLegalQA()

def load_predefined_questions():
    """Load predefined questions from file"""
    try:
        with open('data/questions_short.txt', 'r', encoding='utf-8') as f:
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        logger.warning("questions_short.txt not found")
        return [
            "What is the contract name?",
            "Who are the parties involved?",
            "What is the agreement date?",
            "What is the governing law?",
            "What are the termination conditions?"
        ]

@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "models_loaded": qa_system.qa_pipeline is not None,
        "device": str(qa_system.device)
    })

@app.route('/questions')
def get_questions():
    """Get predefined questions"""
    if qa_system.questions_cache is None:
        qa_system.questions_cache = load_predefined_questions()
    return jsonify(qa_system.questions_cache)

@app.route('/analyze', methods=['POST'])
def analyze_document():
    """Main endpoint for document analysis"""
    try:
        # Get file and question
        file = request.files.get('file')
        question = request.form.get('question', '').strip()
        
        if not file:
            return jsonify({"error": "No file provided"}), 400
        
        if not question:
            return jsonify({"error": "No question provided"}), 400
        
        # Extract text from file
        file_content = file.read()
        extracted_text = qa_system.extract_text_from_file(file_content, file.filename)
        
        if not extracted_text:
            return jsonify({"error": "Could not extract readable text from file"}), 400
        
        logger.info(f"Processing question: {question}")
        logger.info(f"Document length: {len(extracted_text)} characters")
        
        # Get predictions
        predictions = qa_system.predict_answer(question, extracted_text)
        
        if not predictions:
            return jsonify([{
                "answer": "No answer found in the document",
                "confidence": "0%",
                "sentiment": "Neutral",
                "explanation": "The document may not contain relevant information for this question."
            }])
        
        # Process results
        results = []
        for i, pred in enumerate(predictions[:5]):  # Limit to top 5
            answer = pred.get("answer", "")
            confidence = pred.get("confidence", 0)
            
            # Skip very low confidence answers
            if confidence < 5 and i > 0:
                continue
                
            sentiment = qa_system.analyze_sentiment(answer)
            
            results.append({
                "answer": answer,
                "confidence": f"{confidence}%",
                "sentiment": sentiment,
                "explanation": f"Found with {confidence}% confidence"
            })
        
        return jsonify(results if results else [{
            "answer": "No reliable answer found",
            "confidence": "0%",
            "sentiment": "Neutral",
            "explanation": "The model could not find a confident answer in the document."
        }])
        
    except Exception as e:
        logger.error(f"Analysis error: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/paraphrase', methods=['POST'])
def paraphrase_text():
    """Generate paraphrases for better understanding"""
    try:
        text = request.json.get('text', '').strip()
        
        if not text:
            return jsonify({"error": "No text provided"}), 400
        
        paraphrases = qa_system.generate_paraphrases(text)
        return jsonify({"paraphrases": paraphrases})
        
    except Exception as e:
        logger.error(f"Paraphrase error: {str(e)}")
        return jsonify({"error": "Error generating paraphrases"}), 500

@app.route('/validate-question', methods=['POST'])
def validate_question():
    """Validate user-defined questions"""
    try:
        question = request.json.get('question', '').strip()
        
        if not question:
            return jsonify({"valid": False, "message": "Question cannot be empty"})
        
        if len(question) < 5:
            return jsonify({"valid": False, "message": "Question too short"})
        
        if len(question) > 200:
            return jsonify({"valid": False, "message": "Question too long (max 200 characters)"})
        
        # Check if it's a valid question format
        if not any(word in question.lower() for word in ['what', 'who', 'when', 'where', 'how', 'which', 'why', 'is', 'are', 'does', 'do']):
            return jsonify({"valid": False, "message": "Please phrase as a question"})
        
        return jsonify({"valid": True, "message": "Question is valid"})
        
    except Exception as e:
        return jsonify({"valid": False, "message": "Error validating question"})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)