"""
Quality Score Calculator for OCR Extracted Data
Calculates confidence/quality score based on multiple factors
"""
from typing import Dict, Any
import re
from datetime import datetime


class QualityScoreCalculator:
    """
    Calculates quality score (0.0 to 1.0) for extracted document data
    
    Scoring Factors:
    1. Data Completeness (40%) - Are required fields present?
    2. Field Validation (30%) - Are values in correct format?
    3. Data Consistency (20%) - Do values make logical sense?
    4. Extraction Confidence (10%) - Based on response quality
    """
    
    # Required fields by document type
    REQUIRED_FIELDS = {
        "prescription": [
            "doctor_name",
            "patient_name",
            "medicines",
            "date"
        ],
        "bill": [
            "provider_name",
            "patient_name",
            "total_amount",
            "date",
            "items"
        ],
        "test_report": [
            "lab_name",
            "patient_name",
            "tests",
            "date"
        ]
    }
    
    # Optional but valuable fields (bonus points)
    OPTIONAL_FIELDS = {
        "prescription": ["diagnosis", "doctor_registration_number", "clinic_name"],
        "bill": ["bill_number", "payment_method", "tax_amount"],
        "test_report": ["report_number", "doctor_name", "reference_ranges"]
    }
    
    @classmethod
    def calculate_score(
        cls,
        extracted_data: Dict[str, Any],
        document_type: str,
        response_metadata: Dict[str, Any] = None
    ) -> float:
        """
        Calculate overall quality score
        
        Args:
            extracted_data: The extracted JSON data
            document_type: prescription, bill, test_report
            response_metadata: Optional metadata from LLM response
            
        Returns:
            Quality score between 0.0 and 1.0
        """
        if not extracted_data or extracted_data.get("error"):
            return 0.0
        
        scores = {
            "completeness": cls._score_completeness(extracted_data, document_type),
            "validation": cls._score_validation(extracted_data, document_type),
            "consistency": cls._score_consistency(extracted_data, document_type),
            "confidence": cls._score_confidence(response_metadata)
        }
        
        # Weighted average
        weights = {
            "completeness": 0.40,
            "validation": 0.30,
            "consistency": 0.20,
            "confidence": 0.10
        }
        
        total_score = sum(scores[key] * weights[key] for key in scores)
        
        # Round to 2 decimal places
        return round(total_score, 2)
    
    @classmethod
    def _score_completeness(cls, data: Dict, doc_type: str) -> float:
        """
        Score based on presence of required and optional fields
        
        Returns: 0.0 to 1.0
        """
        required = cls.REQUIRED_FIELDS.get(doc_type, [])
        optional = cls.OPTIONAL_FIELDS.get(doc_type, [])
        
        if not required:
            return 0.8  # Unknown document type, give benefit of doubt
        
        # Check required fields (70% of completeness score)
        required_present = sum(1 for field in required if cls._field_has_value(data, field))
        required_score = (required_present / len(required)) * 0.7
        
        # Check optional fields (30% of completeness score)
        if optional:
            optional_present = sum(1 for field in optional if cls._field_has_value(data, field))
            optional_score = (optional_present / len(optional)) * 0.3
        else:
            optional_score = 0.3  # Full bonus if no optional fields defined
        
        return required_score + optional_score
    
    @classmethod
    def _field_has_value(cls, data: Dict, field: str) -> bool:
        """Check if field exists and has meaningful value"""
        value = data.get(field)
        
        if value is None:
            return False
        
        if isinstance(value, str):
            return len(value.strip()) > 0
        
        if isinstance(value, (list, dict)):
            return len(value) > 0
        
        return True
    
    @classmethod
    def _score_validation(cls, data: Dict, doc_type: str) -> float:
        """
        Score based on field format validation
        
        Returns: 0.0 to 1.0
        """
        validations = []
        
        # Date validation
        if "date" in data:
            validations.append(cls._validate_date(data["date"]))
        
        # Amount validation (for bills)
        if "total_amount" in data:
            validations.append(cls._validate_amount(data["total_amount"]))
        
        # Name validation
        for name_field in ["doctor_name", "patient_name", "provider_name", "lab_name"]:
            if name_field in data:
                validations.append(cls._validate_name(data[name_field]))
        
        # List validation (medicines, items, tests)
        for list_field in ["medicines", "items", "tests"]:
            if list_field in data:
                validations.append(cls._validate_list(data[list_field]))
        
        if not validations:
            return 0.7  # No validations performed, neutral score
        
        return sum(validations) / len(validations)
    
    @classmethod
    def _validate_date(cls, date_value: Any) -> float:
        """Validate date format and reasonableness"""
        if not date_value:
            return 0.0
        
        date_str = str(date_value)
        
        # Try common date formats
        formats = ["%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d", "%d %b %Y", "%d %B %Y"]
        
        for fmt in formats:
            try:
                parsed_date = datetime.strptime(date_str, fmt)
                
                # Check if date is reasonable (not in future, not too old)
                now = datetime.now()
                if parsed_date > now:
                    return 0.5  # Future date is suspicious
                
                years_ago = (now - parsed_date).days / 365
                if years_ago > 5:
                    return 0.7  # Very old document
                
                return 1.0  # Valid and reasonable date
            except ValueError:
                continue
        
        # Date string present but couldn't parse
        return 0.3
    
    @classmethod
    def _validate_amount(cls, amount: Any) -> float:
        """Validate monetary amount"""
        if amount is None:
            return 0.0
        
        try:
            # Convert to float
            if isinstance(amount, str):
                # Remove currency symbols and commas
                amount_str = re.sub(r'[₹$,\s]', '', amount)
                amount_val = float(amount_str)
            else:
                amount_val = float(amount)
            
            # Check if reasonable (between 1 and 1,000,000)
            if 1 <= amount_val <= 1000000:
                return 1.0
            elif amount_val > 0:
                return 0.7  # Positive but unusual amount
            else:
                return 0.0  # Invalid amount
        except (ValueError, TypeError):
            return 0.0
    
    @classmethod
    def _validate_name(cls, name: Any) -> float:
        """Validate person/organization name"""
        if not name or not isinstance(name, str):
            return 0.0
        
        name = name.strip()
        
        # Check length
        if len(name) < 2:
            return 0.0
        
        # Check if contains at least some letters
        if not re.search(r'[a-zA-Z]', name):
            return 0.0
        
        # Check if reasonable length
        if len(name) > 100:
            return 0.5  # Suspiciously long
        
        # Check if has proper capitalization (bonus)
        if name[0].isupper():
            return 1.0
        
        return 0.8
    
    @classmethod
    def _validate_list(cls, items: Any) -> float:
        """Validate list fields (medicines, items, tests)"""
        if not isinstance(items, list):
            return 0.0
        
        if len(items) == 0:
            return 0.0
        
        # Check if list items have structure
        if all(isinstance(item, dict) for item in items):
            # Structured data (better quality)
            return 1.0
        elif all(isinstance(item, str) for item in items):
            # Simple strings (acceptable)
            return 0.8
        else:
            # Mixed or unknown structure
            return 0.5
    
    @classmethod
    def _score_consistency(cls, data: Dict, doc_type: str) -> float:
        """
        Score based on logical consistency of data
        
        Returns: 0.0 to 1.0
        """
        consistency_checks = []
        
        # Check if amounts add up (for bills)
        if doc_type == "bill" and "items" in data and "total_amount" in data:
            consistency_checks.append(cls._check_amount_consistency(data))
        
        # Check if medicine count matches (for prescriptions)
        if doc_type == "prescription" and "medicines" in data:
            medicines = data["medicines"]
            if isinstance(medicines, list) and len(medicines) > 0:
                consistency_checks.append(1.0)
            else:
                consistency_checks.append(0.5)
        
        # Check if patient name appears in multiple fields
        patient_name = data.get("patient_name", "").lower()
        if patient_name:
            # Bonus if patient name is consistent
            consistency_checks.append(1.0)
        
        if not consistency_checks:
            return 0.8  # No consistency checks, neutral score
        
        return sum(consistency_checks) / len(consistency_checks)
    
    @classmethod
    def _check_amount_consistency(cls, data: Dict) -> float:
        """Check if item amounts sum to total"""
        try:
            items = data.get("items", [])
            total = float(str(data.get("total_amount", 0)).replace('₹', '').replace(',', ''))
            
            if not items or total == 0:
                return 0.7
            
            # Try to sum item amounts
            item_sum = 0
            for item in items:
                if isinstance(item, dict) and "amount" in item:
                    item_sum += float(str(item["amount"]).replace('₹', '').replace(',', ''))
            
            # Check if within 10% tolerance
            if item_sum > 0:
                diff_percent = abs(total - item_sum) / total
                if diff_percent < 0.1:
                    return 1.0
                elif diff_percent < 0.2:
                    return 0.7
                else:
                    return 0.4
            
            return 0.7
        except:
            return 0.7
    
    @classmethod
    def _score_confidence(cls, metadata: Dict = None) -> float:
        """
        Score based on LLM response metadata
        
        Returns: 0.0 to 1.0
        """
        if not metadata:
            return 0.8  # No metadata, assume good
        
        # Check finish reason
        finish_reason = metadata.get("finish_reason", "")
        if finish_reason == "stop":
            return 1.0  # Normal completion
        elif finish_reason == "length":
            return 0.6  # Truncated response
        else:
            return 0.7
    
    @classmethod
    def get_score_breakdown(
        cls,
        extracted_data: Dict[str, Any],
        document_type: str,
        response_metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Get detailed score breakdown for debugging
        
        Returns:
            {
                "overall_score": 0.85,
                "breakdown": {
                    "completeness": 0.90,
                    "validation": 0.85,
                    "consistency": 0.80,
                    "confidence": 1.0
                },
                "missing_required": ["field1", "field2"],
                "invalid_fields": ["field3"]
            }
        """
        scores = {
            "completeness": cls._score_completeness(extracted_data, document_type),
            "validation": cls._score_validation(extracted_data, document_type),
            "consistency": cls._score_consistency(extracted_data, document_type),
            "confidence": cls._score_confidence(response_metadata)
        }
        
        overall = cls.calculate_score(extracted_data, document_type, response_metadata)
        
        # Find missing required fields
        required = cls.REQUIRED_FIELDS.get(document_type, [])
        missing = [f for f in required if not cls._field_has_value(extracted_data, f)]
        
        return {
            "overall_score": overall,
            "breakdown": scores,
            "missing_required": missing,
            "weights": {
                "completeness": 0.40,
                "validation": 0.30,
                "consistency": 0.20,
                "confidence": 0.10
            }
        }
