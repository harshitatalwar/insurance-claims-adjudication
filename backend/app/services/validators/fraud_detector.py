from typing import Dict, List, Any

class FraudDetector:
    """Detects potential fraud patterns"""
    
    def detect(self, extracted_data: Dict[str, Any], policy_holder: Dict[str, Any]) -> Dict[str, Any]:
        """
        Checks:
        - High amounts
        - Suspicious patterns (Future)
        """
        indicators = []
        
        # Check for unusually high amounts
        amount = extracted_data.get("total_amount", 0)
        if amount > 20000:
            indicators.append("HIGH_VALUE_CLAIM")
        
        # Future: Duplicate claim check (needs DB access or history passed in)
        
        return {
            "suspicious": len(indicators) > 0,
            "indicators": indicators
        }
