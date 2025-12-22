from typing import Dict, List, Any

class DocumentValidator:
    """Validates document completeness and authenticity"""
    
    def validate(self, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Checks:
        - Required fields presence
        - Doctor registration for prescriptions
        """
        errors = []
        
        # Check required fields
        required_fields = ["patient_name", "date", "total_amount"]
        for field in required_fields:
            if not extracted_data.get(field):
                errors.append(f"MISSING_FIELD_{field.upper()}")
        
        # Check doctor registration (if prescription)
        if extracted_data.get("document_type") == "prescription":
            if not extracted_data.get("doctor_registration_number"):
                errors.append("DOCTOR_REG_MISSING")
        
        return {
            "passed": len(errors) == 0,
            "errors": errors
        }
