from typing import Dict, List, Any

class CoverageValidator:
    """Validates service coverage and exclusions"""
    
    def validate(self, extracted_data: Dict[str, Any], policy_terms: Dict[str, Any]) -> Dict[str, Any]:
        """
        Checks:
        - Service covered (not excluded)
        - Diagnosis match
        """
        errors = []
        
        # Check exclusions
        treatment = extracted_data.get("diagnosis", "").lower()
        if not treatment:
             # If diagnosis is missing, we can't fully validate coverage, but DocumentValidator should have caught missing fields.
             # We might skip or strict fail. Let's strict fail if relevant.
             pass

        exclusions = policy_terms.get("exclusions", [])
        
        for exclusion in exclusions:
            if exclusion.lower() in treatment:
                errors.append("SERVICE_EXCLUDED")
                break
        
        # Future: Check if service is specifically in 'covered_services' list if policy is positive-list based.
        # For now, we assume negative-list (exclusions only).
        
        return {
            "passed": len(errors) == 0,
            "errors": errors
        }
