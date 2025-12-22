"""
Database-Based Policy Terms Loader

Loads policy terms from PostgreSQL database instead of static JSON files.
This ensures dynamic policy updates by admins are respected.

Architecture:
- Primary: Load from database (PolicyTerms table)
- Fallback: Load from JSON file if database unavailable
"""
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def load_policy_terms_from_db(
    db: Session,
    policy_terms_id: str = "PLUM_OPD_2024"
) -> Optional[Dict[str, Any]]:
    """
    Load policy terms from database
    
    Args:
        db: Database session
        policy_terms_id: Policy terms ID (e.g., "PLUM_OPD_2024")
        
    Returns:
        Policy terms dict or None if not found
    """
    try:
        from app.models.models import PolicyTerms
        
        # Query database for policy terms
        policy_terms = db.query(PolicyTerms).filter(
            PolicyTerms.policy_id == policy_terms_id
        ).first()
        
        if not policy_terms:
            logger.warning(f"⚠️  Policy terms '{policy_terms_id}' not found in database")
            return None
        
        # Convert SQLAlchemy model to dict
        terms_dict = {
            "policy_id": policy_terms.policy_id,
            "policy_name": policy_terms.policy_name or "Unknown Policy",
            "effective_date": policy_terms.effective_date.isoformat() if policy_terms.effective_date else None,
            
            # Coverage details
            "coverage_details": {
                "annual_limit": float(policy_terms.annual_limit) if policy_terms.annual_limit else 50000.0,
                "per_claim_limit": float(policy_terms.per_claim_limit) if policy_terms.per_claim_limit else 5000.0,
                "family_floater_limit": float(policy_terms.family_floater_limit) if policy_terms.family_floater_limit else 150000.0,
            },
            
            # Sub-limits
            "consultation_fees": {
                "covered": True,
                "limit": float(policy_terms.consultation_limit) if policy_terms.consultation_limit else 5000.0,
                "copay_percentage": float(policy_terms.consultation_copay) if policy_terms.consultation_copay else 0.0
            },
            "pharmacy": {
                "covered": True,
                "limit": float(policy_terms.pharmacy_limit) if policy_terms.pharmacy_limit else 10000.0,
                "copay_percentage": float(policy_terms.pharmacy_copay) if policy_terms.pharmacy_copay else 0.0
            },
            "diagnostic_tests": {
                "covered": True,
                "limit": float(policy_terms.diagnostic_limit) if policy_terms.diagnostic_limit else 8000.0,
                "copay_percentage": float(policy_terms.diagnostic_copay) if policy_terms.diagnostic_copay else 0.0
            },
            "dental": {
                "covered": True,
                "limit": float(policy_terms.dental_limit) if policy_terms.dental_limit else 3000.0,
                "copay_percentage": float(policy_terms.dental_copay) if policy_terms.dental_copay else 0.0
            },
            "vision": {
                "covered": True,
                "limit": float(policy_terms.vision_limit) if policy_terms.vision_limit else 2000.0,
                "copay_percentage": float(policy_terms.vision_copay) if policy_terms.vision_copay else 0.0
            },
            "alternative_medicine": {
                "covered": True,
                "limit": float(policy_terms.alternative_medicine_limit) if policy_terms.alternative_medicine_limit else 5000.0,
                "copay_percentage": float(policy_terms.alternative_medicine_copay) if policy_terms.alternative_medicine_copay else 0.0
            },
            
            # Waiting periods
            "waiting_periods": {
                "initial_waiting": int(policy_terms.initial_waiting_period) if policy_terms.initial_waiting_period else 30,
                "pre_existing_diseases": int(policy_terms.pre_existing_waiting_period) if policy_terms.pre_existing_waiting_period else 365,
                "maternity": 270,  # Not in current schema, using default
                "specific_ailments": {
                    "diabetes": 90,
                    "hypertension": 90,
                    "joint_replacement": 730
                }
            },
            
            # Exclusions
            "exclusions": policy_terms.exclusions or [],
            
            # Network
            "network_discount": float(policy_terms.network_discount) if policy_terms.network_discount else 0.0,
            
            # Minimum claim amount
            "minimum_claim_amount": float(policy_terms.minimum_claim_amount) if policy_terms.minimum_claim_amount else 500.0
        }
        
        logger.info(f"✅ Loaded policy terms from database: {policy_terms_id}")
        return terms_dict
        
    except Exception as e:
        logger.error(f"❌ Failed to load policy terms from database: {e}")
        return None


def load_policy_terms_from_json(
    policy_id: str = "PLUM_OPD_2024"
) -> Optional[Dict[str, Any]]:
    """
    Load policy terms from JSON file (fallback)
    
    Args:
        policy_id: Policy ID
        
    Returns:
        Policy terms dict or None if not found
    """
    try:
        # Try multiple possible locations
        possible_paths = [
            Path(__file__).parent.parent.parent.parent / "plum_intern_assignment" / "policy_terms.json",
            Path(__file__).parent.parent.parent / "policy_terms.json",
            Path("policy_terms.json")
        ]
        
        for policy_file in possible_paths:
            if policy_file.exists():
                with open(policy_file, 'r', encoding='utf-8') as f:
                    terms = json.load(f)
                logger.info(f"✅ Loaded policy terms from JSON: {policy_file}")
                return terms
        
        logger.warning(f"⚠️  Policy terms JSON file not found")
        return None
        
    except Exception as e:
        logger.error(f"❌ Failed to load policy terms from JSON: {e}")
        return None


def get_policy_terms(
    db: Optional[Session] = None,
    policy_terms_id: str = "PLUM_OPD_2024",
    use_fallback: bool = True
) -> Dict[str, Any]:
    """
    Get policy terms with database-first approach
    
    Priority:
    1. Load from database (if db session provided)
    2. Fallback to JSON file (if use_fallback=True)
    3. Return empty dict (if all fail)
    
    Args:
        db: Database session (optional)
        policy_terms_id: Policy terms ID
        use_fallback: Whether to fallback to JSON if database fails
        
    Returns:
        Policy terms dict (never None, returns {} if all fail)
    """
    # Try database first
    if db:
        terms = load_policy_terms_from_db(db, policy_terms_id)
        if terms:
            return terms
        logger.warning(f"⚠️  Database load failed, trying fallback...")
    
    # Fallback to JSON
    if use_fallback:
        terms = load_policy_terms_from_json(policy_terms_id)
        if terms:
            logger.warning(f"⚠️  Using JSON fallback for policy terms")
            return terms
    
    # All failed - return empty dict
    logger.error(f"❌ Failed to load policy terms from all sources")
    return {}
