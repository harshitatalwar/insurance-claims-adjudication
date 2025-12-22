from typing import Dict, List, Any

class LimitValidator:
    """Validates financial limits and calculates copay"""
    
    def validate(self, amount: float, policy_holder: Dict[str, Any], extracted_data: Dict[str, Any], policy_terms: Dict[str, Any]) -> Dict[str, Any]:
        """
        Checks:
        - Per claim limit
        - Annual limit
        Calculates:
        - Copay
        - Approved amount
        """
        errors = []
        
        # Get limits from policy terms
        coverage_details = policy_terms.get("coverage_details", {})
        annual_limit = coverage_details.get("annual_limit", 50000)
        per_claim_limit = coverage_details.get("per_claim_limit", 5000)
        
        # Check per-claim limit
        if amount > per_claim_limit:
            errors.append("PER_CLAIM_LIMIT_EXCEEDED")
        
        # Check annual limit
        annual_used = policy_holder.get("annual_limit_used", 0)
        if annual_used + amount > annual_limit:
            errors.append("ANNUAL_LIMIT_EXCEEDED")
        
        # Calculate copay
        # Determine category based on treatment type or default to consultation
        treatment_type = extracted_data.get("treatment_type", "consultation").lower()
        
        fees_config = coverage_details.get(f"{treatment_type}_fees", coverage_details.get("consultation_fees", {}))
        copay_pct = fees_config.get("copay_percentage", 10)
        
        copay_amount = amount * (copay_pct / 100)
        approved_amount = amount - copay_amount
        
        # If limits exceeded, approved amount is 0? 
        # Usually yes, or capped. The requirement implies strict rejection if limit exceeded for now.
        if errors:
            approved_amount = 0
            
        return {
            "passed": len(errors) == 0,
            "errors": errors,
            "approved_amount": approved_amount,
            "copay_amount": copay_amount,
            "copay_percentage": copay_pct
        }
