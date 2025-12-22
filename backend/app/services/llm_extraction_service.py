"""
LLM Extraction Service - Extract structured data from OCR text using OpenAI
"""
from openai import OpenAI
from typing import Dict, Any, Optional
import json
from app.config import settings
from app.schemas import PrescriptionData, BillData

class LLMExtractionService:
    def __init__(self):
        self.client = None
        self.model = "gpt-4o-mini"  # Cost-effective model
    
    def _get_client(self):
        """Lazy-load OpenAI client"""
        if self.client is None:
            if not settings.OPENAI_API_KEY:
                raise ValueError("OPENAI_API_KEY not set in environment variables")
            self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        return self.client
    
    def extract_prescription_data(self, ocr_text: str) -> Dict[str, Any]:
        """Extract structured prescription data from OCR text"""
        
        prompt = f"""
You are a medical document data extraction expert. Extract the following information from this prescription text.

Return ONLY a valid JSON object with these exact fields:
{{
    "doctor_name": "string or null",
    "doctor_registration": "string or null (format: STATE/NUMBER/YEAR)",
    "patient_name": "string or null",
    "patient_age": "string or null",
    "diagnosis": "string or null",
    "medicines": [
        {{"name": "medicine name", "dosage": "dosage", "duration": "duration"}}
    ],
    "tests_advised": ["test1", "test2"],
    "date": "string or null (YYYY-MM-DD format if possible)"
}}

Prescription Text:
{ocr_text}

Return ONLY the JSON object, no other text.
"""
        
        try:
            client = self._get_client()
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a medical data extraction expert. Always return valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            return result
        
        except Exception as e:
            print(f"Error extracting prescription data: {e}")
            return {
                "doctor_name": None,
                "doctor_registration": None,
                "patient_name": None,
                "patient_age": None,
                "diagnosis": None,
                "medicines": [],
                "tests_advised": [],
                "date": None,
                "extraction_error": str(e)
            }
    
    def extract_bill_data(self, ocr_text: str) -> Dict[str, Any]:
        """Extract structured bill data from OCR text"""
        
        prompt = f"""
You are a medical billing data extraction expert. Extract the following information from this medical bill.

Return ONLY a valid JSON object with these exact fields:
{{
    "bill_number": "string or null",
    "hospital_name": "string or null",
    "patient_name": "string or null",
    "date": "string or null (YYYY-MM-DD format if possible)",
    "consultation_fee": number or null,
    "diagnostic_tests": number or null,
    "medicines": number or null,
    "total_amount": number or null,
    "items": [
        {{"description": "item description", "amount": number}}
    ]
}}

Bill Text:
{ocr_text}

Return ONLY the JSON object, no other text.
"""
        
        try:
            client = self._get_client()
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a medical billing data extraction expert. Always return valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            return result
        
        except Exception as e:
            print(f"Error extracting bill data: {e}")
            return {
                "bill_number": None,
                "hospital_name": None,
                "patient_name": None,
                "date": None,
                "consultation_fee": None,
                "diagnostic_tests": None,
                "medicines": None,
                "total_amount": None,
                "items": [],
                "extraction_error": str(e)
            }
    
    def validate_extracted_data(self, extracted_data: Dict[str, Any], claim_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate extracted data against claim data
        Returns validation errors
        """
        errors = []
        
        # Check patient name match (if available)
        if extracted_data.get("patient_name") and claim_data.get("policy_holder_name"):
            extracted_name = extracted_data["patient_name"].lower()
            claim_name = claim_data["policy_holder_name"].lower()
            
            # Simple fuzzy match (check if names share common words)
            if not any(word in claim_name for word in extracted_name.split() if len(word) > 2):
                errors.append("PATIENT_MISMATCH")
        
        # Check date consistency
        if extracted_data.get("date") and claim_data.get("treatment_date"):
            # Would need proper date parsing here
            pass
        
        # Check amount consistency (for bills)
        if "total_amount" in extracted_data and "claimed_amount" in claim_data:
            extracted_amount = extracted_data.get("total_amount")
            claimed_amount = claim_data.get("claimed_amount")
            
            if extracted_amount and claimed_amount:
                # Allow 5% variance
                variance = abs(extracted_amount - claimed_amount) / claimed_amount
                if variance > 0.05:
                    errors.append("AMOUNT_MISMATCH")
        
        return {
            "is_valid": len(errors) == 0,
            "errors": errors
        }
    
    def extract_and_validate(self, ocr_text: str, document_type: str, claim_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract data and validate in one step
        """
        if document_type == "prescription":
            extracted = self.extract_prescription_data(ocr_text)
        elif document_type == "bill":
            extracted = self.extract_bill_data(ocr_text)
        else:
            extracted = {}
        
        validation = self.validate_extracted_data(extracted, claim_data)
        
        return {
            "extracted_data": extracted,
            "validation": validation
        }
