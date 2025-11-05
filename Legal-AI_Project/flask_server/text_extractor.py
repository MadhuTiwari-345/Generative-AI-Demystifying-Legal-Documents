"""
Enhanced text extraction module with PyMuPDF for robust document processing
"""

import fitz  # PyMuPDF
import re
import os
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class EnhancedTextExtractor:
    """Advanced text extraction with layout preservation and OCR support"""
    
    def __init__(self):
        self.supported_formats = {
            '.pdf': self._extract_from_pdf,
            '.txt': self._extract_from_text,
            '.doc': self._extract_from_text,
            '.docx': self._extract_from_text
        }
    
    def extract_text(self, file_content: bytes, filename: str) -> Optional[str]:
        """
        Extract text from various file formats with enhanced processing
        
        Args:
            file_content: Raw file bytes
            filename: Original filename with extension
            
        Returns:
            Extracted and cleaned text or None if extraction fails
        """
        try:
            file_ext = self._get_file_extension(filename)
            
            if file_ext in self.supported_formats:
                extractor = self.supported_formats[file_ext]
                raw_text = extractor(file_content)
                
                if raw_text:
                    return self._clean_and_normalize_text(raw_text)
            
            # Fallback to text extraction with multiple encodings
            return self._extract_with_fallback_encoding(file_content)
            
        except Exception as e:
            logger.error(f"Text extraction failed for {filename}: {str(e)}")
            return None
    
    def _extract_from_pdf(self, file_content: bytes) -> Optional[str]:
        """Extract text from PDF with layout preservation"""
        try:
            doc = fitz.open(stream=file_content, filetype="pdf")
            
            if doc.is_encrypted:
                logger.warning("PDF is encrypted, attempting to decrypt")
                if not doc.authenticate(""):
                    return None
            
            extracted_text = ""
            
            for page_num in range(doc.page_count):
                page = doc[page_num]
                
                # Try different extraction methods for best results
                text_methods = [
                    lambda p: p.get_text("text"),  # Standard text
                    lambda p: p.get_text("dict"),  # Structured text with formatting
                    lambda p: p.get_text("blocks") # Text blocks
                ]
                
                page_text = ""
                for method in text_methods:
                    try:
                        result = method(page)
                        if isinstance(result, str) and result.strip():
                            page_text = result
                            break
                        elif isinstance(result, dict):
                            page_text = self._extract_from_dict_structure(result)
                            if page_text.strip():
                                break
                        elif isinstance(result, list):
                            page_text = self._extract_from_blocks(result)
                            if page_text.strip():
                                break
                    except Exception as e:
                        logger.debug(f"Text extraction method failed: {str(e)}")
                        continue
                
                # If no text found, try OCR-like extraction
                if not page_text.strip():
                    try:
                        # Get text with coordinates for better layout understanding
                        text_dict = page.get_text("dict")
                        page_text = self._extract_with_layout_awareness(text_dict)
                    except Exception as e:
                        logger.debug(f"Layout-aware extraction failed: {str(e)}")
                
                extracted_text += page_text + "\n\n"
            
            doc.close()
            return extracted_text.strip()
            
        except Exception as e:
            logger.error(f"PDF extraction error: {str(e)}")
            return None
    
    def _extract_from_text(self, file_content: bytes) -> Optional[str]:
        """Extract text from text-based files with encoding detection"""
        return self._extract_with_fallback_encoding(file_content)
    
    def _extract_with_fallback_encoding(self, file_content: bytes) -> Optional[str]:
        """Try multiple encodings to extract text"""
        encodings = ['utf-8', 'utf-16', 'latin-1', 'cp1252', 'iso-8859-1', 'ascii']
        
        for encoding in encodings:
            try:
                text = file_content.decode(encoding)
                if self._is_readable_text(text):
                    return text
            except (UnicodeDecodeError, UnicodeError):
                continue
        
        return None
    
    def _extract_from_dict_structure(self, text_dict: Dict[str, Any]) -> str:
        """Extract text from PyMuPDF dictionary structure"""
        text = ""
        
        try:
            for block in text_dict.get("blocks", []):
                if "lines" in block:
                    for line in block["lines"]:
                        for span in line.get("spans", []):
                            text += span.get("text", "") + " "
                        text += "\n"
                elif "text" in block:
                    text += block["text"] + "\n"
        except Exception as e:
            logger.debug(f"Dict structure extraction error: {str(e)}")
        
        return text
    
    def _extract_from_blocks(self, blocks: list) -> str:
        """Extract text from PyMuPDF blocks structure"""
        text = ""
        
        try:
            for block in blocks:
                if isinstance(block, tuple) and len(block) >= 5:
                    # Block format: (x0, y0, x1, y1, "text", block_no, block_type)
                    if len(block) > 4:
                        text += str(block[4]) + "\n"
                elif isinstance(block, str):
                    text += block + "\n"
        except Exception as e:
            logger.debug(f"Blocks extraction error: {str(e)}")
        
        return text
    
    def _extract_with_layout_awareness(self, text_dict: Dict[str, Any]) -> str:
        """Extract text with layout awareness for better structure preservation"""
        lines_by_y = {}
        
        try:
            for block in text_dict.get("blocks", []):
                if "lines" in block:
                    for line in block["lines"]:
                        y_coord = line.get("bbox", [0, 0, 0, 0])[1]  # y0 coordinate
                        line_text = ""
                        
                        for span in line.get("spans", []):
                            line_text += span.get("text", "") + " "
                        
                        if line_text.strip():
                            if y_coord not in lines_by_y:
                                lines_by_y[y_coord] = []
                            lines_by_y[y_coord].append(line_text.strip())
            
            # Sort by y-coordinate and join
            sorted_lines = []
            for y in sorted(lines_by_y.keys()):
                sorted_lines.append(" ".join(lines_by_y[y]))
            
            return "\n".join(sorted_lines)
            
        except Exception as e:
            logger.debug(f"Layout-aware extraction error: {str(e)}")
            return ""
    
    def _clean_and_normalize_text(self, text: str) -> str:
        """Clean and normalize extracted text"""
        if not text:
            return ""
        
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'\n\s*\n', '\n\n', text)
        
        # Remove common PDF artifacts
        text = re.sub(r'[^\w\s\.\,\;\:\!\?\-\(\)\[\]\{\}\"\'\/\@\#\$\%\&\*\+\=\<\>\|\\\~\`\n]', '', text)
        
        # Fix common OCR errors
        text = re.sub(r'\b(\w)\s+(\w)\b', r'\1\2', text)  # Fix spaced letters
        text = re.sub(r'(\w)\s*-\s*(\w)', r'\1-\2', text)  # Fix hyphenated words
        
        # Normalize quotes and apostrophes
        text = re.sub(r'["""]', '"', text)
        text = re.sub(r'[''']', "'", text)
        
        # Remove excessive punctuation
        text = re.sub(r'\.{3,}', '...', text)
        text = re.sub(r'-{2,}', '--', text)
        
        return text.strip()
    
    def _is_readable_text(self, text: str) -> bool:
        """Check if extracted text is readable and meaningful"""
        if not text or len(text.strip()) < 10:
            return False
        
        # Check for reasonable character distribution
        printable_chars = sum(1 for c in text if c.isprintable())
        total_chars = len(text)
        
        if total_chars == 0:
            return False
        
        printable_ratio = printable_chars / total_chars
        
        # Should have mostly printable characters
        if printable_ratio < 0.8:
            return False
        
        # Should have some alphabetic characters
        alpha_chars = sum(1 for c in text if c.isalpha())
        alpha_ratio = alpha_chars / total_chars
        
        if alpha_ratio < 0.3:
            return False
        
        return True
    
    def _get_file_extension(self, filename: str) -> str:
        """Get file extension in lowercase"""
        return os.path.splitext(filename.lower())[1]
    
    def get_document_info(self, file_content: bytes, filename: str) -> Dict[str, Any]:
        """Get document metadata and extraction info"""
        info = {
            "filename": filename,
            "file_size": len(file_content),
            "file_type": self._get_file_extension(filename),
            "extraction_success": False,
            "text_length": 0,
            "is_readable": False,
            "page_count": 0
        }
        
        try:
            if filename.lower().endswith('.pdf'):
                doc = fitz.open(stream=file_content, filetype="pdf")
                info["page_count"] = doc.page_count
                info["is_encrypted"] = doc.is_encrypted
                doc.close()
            
            extracted_text = self.extract_text(file_content, filename)
            if extracted_text:
                info["extraction_success"] = True
                info["text_length"] = len(extracted_text)
                info["is_readable"] = self._is_readable_text(extracted_text)
                
        except Exception as e:
            info["error"] = str(e)
        
        return info

# Global instance for reuse
text_extractor = EnhancedTextExtractor()