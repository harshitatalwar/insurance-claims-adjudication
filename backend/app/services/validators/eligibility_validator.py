from typing import Dict, List, Any
from datetime import datetime
from app.models.models import PolicyStatus
from app.utils.date_parser import parse_date_robust, get_days_between

class EligibilityValidator:
    """Validates policy eligibility criteria"""
    
    def validate(self, policy_holder: Dict[str, Any], extracted_data: Dict[str, Any], policy_terms: Dict[str, Any]) -> Dict[str, Any]:
        """
        Checks:
        - Policy active status
        - Waiting periods (dynamically calculated from join_date)
        """
        errors = []
        
        # Check policy status
        if policy_holder.get("policy_status") != "ACTIVE":
            if policy_holder.get("policy_status") == "SUSPENDED":
                 errors.append("POLICY_SUSPENDED")
            elif policy_holder.get("policy_status") == "INACTIVE":
                 errors.append("POLICY_INACTIVE")
            else:
                 errors.append(f"POLICY_STATUS_{policy_holder.get('policy_status', 'UNKNOWN')}")
        
        # Check waiting period (dynamically calculated)
        # Parse dates robustly (handles various formats from LLM/OCR)
        try:
            join_date_str = policy_holder.get("join_date")
            
            # Get treatment date from various possible locations
            treatment_date_str = None
            if "financials" in extracted_data:
                treatment_date_str = extracted_data["financials"].get("bill_date")
            if not treatment_date_str:
                treatment_date_str = extracted_data.get("date")
            if not treatment_date_str:
                treatment_date_str = extracted_data.get("treatment_date")
            
            if join_date_str and treatment_date_str:
                # Use robust date parser (handles ISO, US, EU, natural formats)
                join_date = parse_date_robust(join_date_str)
                treatment_date = parse_date_robust(treatment_date_str)
                
                if not join_date or not treatment_date:
                    errors.append("DATE_PARSING_ERROR")
                else:
                    # Calculate days between dates
                    days_since_join = get_days_between(join_date, treatment_date)
                    
                    if days_since_join is None:
                        errors.append("DATE_CALCULATION_ERROR")
                    else:
                        # Get initial waiting period from policy terms (default 30 days)
                        initial_waiting = policy_terms.get("waiting_periods", {}).get("initial_waiting", 30)
                        
                        # Dynamic check: Has the initial waiting period passed?
                        if days_since_join < initial_waiting:
                            errors.append("WAITING_PERIOD_NOT_MET")
                        
                        # Note: We check dynamically, ignoring the waiting_period_completed flag in DB
                        # This ensures accurate validation even if the flag wasn't updated
                
        except Exception as e:
            # Robust error handling - log and flag
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Date validation error: {e}")
            errors.append("DATE_VALIDATION_ERROR")

        return {
            "passed": len(errors) == 0,
            "errors": errors
        }
