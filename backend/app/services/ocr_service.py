"""
OCR Service - Extract text from images and PDFs using Tesseract
"""
import pytesseract
from PIL import Image
from pdf2image import convert_from_path
import os
from typing import Optional

class OCRService:
    def __init__(self):
        # Set tesseract path if on Windows
        # pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
        pass
    
    def extract_text_from_image(self, image_path: str) -> str:
        """Extract text from an image file"""
        try:
            image = Image.open(image_path)
            text = pytesseract.image_to_string(image)
            return text.strip()
        except Exception as e:
            print(f"Error extracting text from image: {e}")
            return ""
    
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extract text from a PDF file"""
        try:
            # Convert PDF to images
            images = convert_from_path(pdf_path)
            
            # Extract text from each page
            full_text = []
            for i, image in enumerate(images):
                text = pytesseract.image_to_string(image)
                full_text.append(f"--- Page {i+1} ---\n{text}")
            
            return "\n\n".join(full_text).strip()
        except Exception as e:
            print(f"Error extracting text from PDF: {e}")
            return ""
    
    def extract_text(self, file_path: str) -> str:
        """Extract text from file (auto-detect type)"""
        ext = os.path.splitext(file_path)[1].lower()
        
        if ext in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff']:
            return self.extract_text_from_image(file_path)
        elif ext == '.pdf':
            return self.extract_text_from_pdf(file_path)
        else:
            raise ValueError(f"Unsupported file type: {ext}")
    
    def assess_quality(self, text: str) -> tuple[bool, float]:
        """
        Assess if extracted text is legible
        Returns: (is_legible, quality_score)
        """
        if not text or len(text) < 10:
            return False, 0.0
        
        # Simple quality metrics
        word_count = len(text.split())
        char_count = len(text)
        
        # Check for gibberish (too many special characters)
        special_chars = sum(1 for c in text if not c.isalnum() and not c.isspace())
        special_ratio = special_chars / char_count if char_count > 0 else 1.0
        
        # Quality score based on word count and special char ratio
        quality_score = min(1.0, (word_count / 50) * (1 - special_ratio))
        is_legible = quality_score > 0.3
        
        return is_legible, quality_score
