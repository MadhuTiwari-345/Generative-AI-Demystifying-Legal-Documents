import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

class ParaphraseModel:
    _instance = None
    _model = None
    _tokenizer = None
    _loaded = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            try:
                cls._device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
                print(f"Loading paraphrase model on {cls._device}...")
                cls._tokenizer = AutoTokenizer.from_pretrained("humarin/chatgpt_paraphraser_on_T5_base")
                cls._model = AutoModelForSeq2SeqLM.from_pretrained("humarin/chatgpt_paraphraser_on_T5_base").to(cls._device)
                cls._model.eval()
                cls._loaded = True
                print("Paraphrase model loaded successfully!")
            except Exception as e:
                print(f"Error loading paraphrase model: {str(e)}")
                cls._loaded = False
        return cls._instance
    
    @property
    def model(self):
        return self._model
    
    @property
    def tokenizer(self):
        return self._tokenizer
    
    @property
    def device(self):
        return self._device

# Global instance
_paraphrase_model = ParaphraseModel()

def paraphrase(
    question,
    num_beams=3,
    num_return_sequences=3,
    repetition_penalty=2.0,
    no_repeat_ngram_size=2,
    max_length=128
):
    if not question or question.strip() == "":
        return ["No text to paraphrase"]
    
    # Check if model is loaded
    if not _paraphrase_model._loaded:
        return ["Paraphrase model not available"]
    
    try:
        input_ids = _paraphrase_model.tokenizer(
            f'paraphrase: {question}',
            return_tensors="pt", 
            padding="longest",
            max_length=max_length,
            truncation=True,
        ).input_ids.to(_paraphrase_model.device)
        
        with torch.no_grad():
            outputs = _paraphrase_model.model.generate(
                input_ids, 
                repetition_penalty=repetition_penalty,
                num_return_sequences=num_return_sequences, 
                no_repeat_ngram_size=no_repeat_ngram_size,
                num_beams=num_beams, 
                max_length=max_length,
                do_sample=False
            )

        res = _paraphrase_model.tokenizer.batch_decode(outputs, skip_special_tokens=True)
        return res if res else ["No paraphrase generated"]
    except Exception as e:
        print(f"Paraphrase error: {str(e)}")
        return [f"Error generating paraphrase: {str(e)}"]