"""
Hybrid OCR Service
Combines Tesseract OCR with OpenAI Vision LLM for robust text extraction
"""
import os
import json
from typing import Dict, Optional, Any
from pathlib import Path
import pytesseract
from PIL import Image
import pdf2image
from openai import OpenAI


class HybridOCRService:
    """Combines Tesseract OCR and OpenAI Vision for document processing"""
    
    def __init__(self):
        self._client = None
    
    @property
    def client(self):
        """Lazy load OpenAI client"""
        if self._client is None:
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                self._client = OpenAI(api_key=api_key)
        return self._client
    
    def run_tesseract(self, file_path: str) -> str:
        """
        Extract text using Tesseract OCR
        
        Args:
            file_path: Path to image or PDF file
            
        Returns:
            Extracted text
        """
        try:
            file_ext = Path(file_path).suffix.lower()
            
            if file_ext == '.pdf':
                # Convert PDF to images
                images = pdf2image.convert_from_path(file_path)
                text_parts = []
                for image in images:
                    text = pytesseract.image_to_string(image)
                    text_parts.append(text)
                return "\n\n".join(text_parts)
            else:
                # Process image directly
                image = Image.open(file_path)
                return pytesseract.image_to_string(image)
        except Exception as e:
            print(f"Tesseract OCR error: {e}")
            return ""
    
    def get_extraction_schema(self, doc_type: str) -> Dict[str, Any]:
        """
        Get JSON schema for structured extraction based on document type
        
        Args:
            doc_type: Type of document (prescription, bill, report)
            
        Returns:
            JSON schema dictionary
        """
        if doc_type == "prescription":
            return {
                "type": "object",
                "properties": {
                    "doctor_name": {"type": "string"},
                    "doctor_registration_number": {"type": "string"},
                    "clinic_name": {"type": "string"},
                    "patient_name": {"type": "string"},
                    "date": {"type": "string"},
                    "diagnosis": {"type": "string"},
                    "medicines": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "dosage": {"type": "string"},
                                "frequency": {"type": "string"},
                                "duration": {"type": "string"}
                            }
                        }
                    },
                    "tests_advised": {"type": "array", "items": {"type": "string"}}
                }
            }
        elif doc_type == "bill":
            return {
                "type": "object",
                "properties": {
                    "bill_number": {"type": "string"},
                    "hospital_name": {"type": "string"},
                    "date": {"type": "string"},
                    "patient_name": {"type": "string"},
                    "items": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "description": {"type": "string"},
                                "amount": {"type": "number"}
                            }
                        }
                    },
                    "subtotal": {"type": "number"},
                    "gst": {"type": "number"},
                    "total_amount": {"type": "number"},
                    "payment_mode": {"type": "string"}
                }
            }
        elif doc_type == "report":
            return {
                "type": "object",
                "properties": {
                    "lab_name": {"type": "string"},
                    "report_id": {"type": "string"},
                    "patient_name": {"type": "string"},
                    "date": {"type": "string"},
                    "test_name": {"type": "string"},
                    "results": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "parameter": {"type": "string"},
                                "value": {"type": "string"},
                                "normal_range": {"type": "string"}
                            }
                        }
                    },
                    "remarks": {"type": "string"}
                }
            }
        else:
            return {
                "type": "object",
                "properties": {
                    "content": {"type": "string"}
                }
            }
    
    async def run_vision_llm(self, file_path: str, ocr_text: str, doc_type: str) -> Dict[str, Any]:
        """
        Extract structured data using OpenAI Vision LLM
        
        Args:
            file_path: Path to image file
            ocr_text: Text from Tesseract OCR
            doc_type: Type of document
            
        Returns:
            Extracted structured data
        """
        if not self.client:
            print("OpenAI API key not set, skipping LLM extraction")
            return {}
        
        try:
            # Read image as base64
            import base64
            with open(file_path, "rb") as image_file:
                image_data = base64.b64encode(image_file.read()).decode('utf-8')
            
            schema = self.get_extraction_schema(doc_type)
            
            prompt = f"""
You are a medical document extraction expert. Extract structured information from this {doc_type}.

OCR Text (may have errors):
{ocr_text}

Extract the following information and return as JSON matching this schema:
{json.dumps(schema, indent=2)}

Be precise and only extract information that is clearly visible. If a field is not found, use null.
Return ONLY valid JSON, no additional text.
"""
            
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_data}"
                                }
                            }
                        ]
                    }
                ],
                response_format={"type": "json_object"},
                max_tokens=1500
            )
            
            result = json.loads(response.choices[0].message.content)
            return result
            
        except Exception as e:
            print(f"Vision LLM error: {e}")
            return {}
    
    async def process_document(self, file_path: str, doc_type: str) -> Dict[str, Any]:
        """
        Process document using hybrid OCR approach
        
        Args:
            file_path: Path to document file
            doc_type: Type of document
            
        Returns:
            Dictionary with extracted data and metadata
        """
        # Step 1: Run Tesseract OCR
        ocr_text = self.run_tesseract(file_path)
        
        # Step 2: Run Vision LLM
        llm_data = await self.run_vision_llm(file_path, ocr_text, doc_type)
        
        # Step 3: Calculate confidence score
        confidence = 0.5  # Base confidence from Tesseract
        if llm_data:
            confidence = 0.9  # Higher confidence when LLM succeeds
        
        return {
            "ocr_text": ocr_text,
            "extracted_data": llm_data,
            "confidence_score": confidence,
            "processing_method": "hybrid_ocr_llm" if llm_data else "tesseract_only"
        }
