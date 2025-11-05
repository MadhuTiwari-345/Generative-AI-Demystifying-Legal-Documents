import torch
from transformers import AutoTokenizer, AutoModelForQuestionAnswering, pipeline
import json
import os

def run_prediction_simple(questions, context, model_name='deepset/roberta-base-squad2'):
    """Simplified prediction function without multiprocessing"""
    try:
        print(f"Loading model: {model_name}")
        
        # Use pipeline for simpler, more stable inference
        qa_pipeline = pipeline(
            "question-answering",
            model=model_name,
            tokenizer=model_name,
            device=-1,  # Force CPU to avoid CUDA issues
            return_all_scores=False
        )
        
        results = {}
        
        for i, question in enumerate(questions):
            print(f"Processing question {i+1}: {question}")
            
            # Truncate context if too long
            max_context_length = 2000
            if len(context) > max_context_length:
                context = context[:max_context_length]
            
            try:
                result = qa_pipeline(question=question, context=context)
                
                # Extract answer
                answer = result.get('answer', '').strip()
                confidence = result.get('score', 0)
                
                results[str(i)] = answer
                
                # Create simplified nbest format for compatibility
                nbest_data = {
                    str(i): [
                        {
                            'text': answer,
                            'probability': confidence,
                            'start_logit': confidence,
                            'end_logit': confidence
                        }
                    ]
                }
                
                # Save nbest.json for compatibility with existing code
                with open('nbest.json', 'w', encoding='utf-8') as f:
                    json.dump(nbest_data, f, ensure_ascii=False, indent=2)
                
                print(f"Answer found: {answer} (confidence: {confidence:.3f})")
                
            except Exception as e:
                print(f"Error processing question {i}: {str(e)}")
                results[str(i)] = ""
        
        return results
        
    except Exception as e:
        print(f"Model loading/prediction error: {str(e)}")
        return {"0": ""}

def run_prediction(questions, context, model_name, n_best_size=5):
    """Wrapper function to maintain compatibility with existing code"""
    return run_prediction_simple(questions, context, model_name)