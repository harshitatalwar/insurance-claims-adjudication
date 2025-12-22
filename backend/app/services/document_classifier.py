"""
Document Classification Service
Automatically classifies uploaded documents as prescription, bill, or report
"""
import re
from typing import Optional
from pathlib import Path


class DocumentClassifier:
    """Classifies medical documents based on filename, extension, and content"""
    
    # Document type keywords
    PRESCRIPTION_KEYWORDS = [
        "prescription", "rx", "doctor", "medicine", "tablet", "syrup",
        "dosage", "diagnosis", "dr.", "reg. no", "follow-up"
    ]
    
    BILL_KEYWORDS = [
        "bill", "invoice", "receipt", "payment", "gst", "total",
        "amount", "consultation fee", "hospital", "clinic"
    ]
    
    REPORT_KEYWORDS = [
        "report", "test", "lab", "diagnostic", "pathology",
        "blood", "urine", "x-ray", "ultrasound", "ecg", "mri",
        "result", "normal range", "nabl", "cap accreditation"
    ]
    
    @staticmethod
    def classify_by_filename(filename: str) -> Optional[str]:
        """
        Classify document based on filename
        
        Args:
            filename: Name of the file
            
        Returns:
            Document type or None if cannot determine
        """
        filename_lower = filename.lower()
        
        if any(keyword in filename_lower for keyword in ["prescription", "rx", "presc"]):
            return "prescription"
        elif any(keyword in filename_lower for keyword in ["bill", "invoice", "receipt"]):
            return "bill"
        elif any(keyword in filename_lower for keyword in ["report", "test", "lab"]):
            return "report"
        
        return None
    
    @staticmethod
    def classify_by_extension(filename: str) -> str:
        """
        Get file category based on extension
        
        Args:
            filename: Name of the file
            
        Returns:
            File category: 'image', 'pdf', or 'document'
        """
        ext = Path(filename).suffix.lower()
        
        if ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff']:
            return 'image'
        elif ext == '.pdf':
            return 'pdf'
        elif ext in ['.doc', '.docx']:
            return 'document'
        else:
            return 'unknown'
    
    @staticmethod
    def classify_by_content(text: str) -> str:
        """
        Classify document based on OCR text content
        
        Args:
            text: Extracted text from document
            
        Returns:
            Document type: 'prescription', 'bill', or 'report'
        """
        text_lower = text.lower()
        
        # Count keyword matches for each type
        prescription_score = sum(1 for keyword in DocumentClassifier.PRESCRIPTION_KEYWORDS 
                                if keyword in text_lower)
        bill_score = sum(1 for keyword in DocumentClassifier.BILL_KEYWORDS 
                        if keyword in text_lower)
        report_score = sum(1 for keyword in DocumentClassifier.REPORT_KEYWORDS 
                          if keyword in text_lower)
        
        # Return type with highest score
        scores = {
            'prescription': prescription_score,
            'bill': bill_score,
            'report': report_score
        }
        
        max_type = max(scores, key=scores.get)
        
        # If score is too low, default to 'other'
        if scores[max_type] < 2:
            return 'other'
        
        return max_type
    
    @staticmethod
    def classify(filename: str, ocr_text: Optional[str] = None) -> str:
        """
        Classify document using multiple strategies
        
        Args:
            filename: Name of the file
            ocr_text: Optional OCR text for content-based classification
            
        Returns:
            Document type: 'prescription', 'bill', 'report', or 'other'
        """
        # Try filename first
        doc_type = DocumentClassifier.classify_by_filename(filename)
        if doc_type:
            return doc_type
        
        # If OCR text available, use content classification
        if ocr_text:
            return DocumentClassifier.classify_by_content(ocr_text)
        
        # Default to 'other'
        return 'other'
