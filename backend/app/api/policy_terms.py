"""
PolicyTerms API - Read-only access to policy terms and limits
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.schemas import PolicyTermsResponse
from app.models import PolicyTerms
from app.utils.database import get_db

router = APIRouter()

@router.get("/", response_model=List[PolicyTermsResponse])
async def list_policy_terms(db: Session = Depends(get_db)):
    """List all available policy terms"""
    policies = db.query(PolicyTerms).all()
    return policies

@router.get("/{policy_id}", response_model=PolicyTermsResponse)
async def get_policy_terms(policy_id: str, db: Session = Depends(get_db)):
    """Get specific policy terms by ID"""
    policy = db.query(PolicyTerms).filter(PolicyTerms.policy_id == policy_id).first()
    
    if not policy:
        raise HTTPException(status_code=404, detail="Policy terms not found")
    
    return policy

@router.get("/{policy_id}/limits", response_model=dict)
async def get_policy_limits(policy_id: str, db: Session = Depends(get_db)):
    """Get all limits for a specific policy"""
    policy = db.query(PolicyTerms).filter(PolicyTerms.policy_id == policy_id).first()
    
    if not policy:
        raise HTTPException(status_code=404, detail="Policy terms not found")
    
    return {
        "annual_limit": policy.annual_limit,
        "per_claim_limit": policy.per_claim_limit,
        "sub_limits": {
            "consultation": policy.consultation_limit,
            "diagnostic": policy.diagnostic_limit,
            "pharmacy": policy.pharmacy_limit,
            "dental": policy.dental_limit,
            "vision": policy.vision_limit,
            "alternative_medicine": policy.alternative_medicine_limit
        },
        "copay": {
            "consultation": policy.consultation_copay,
            "branded_drugs": policy.branded_drugs_copay
        },
        "network_discount": policy.network_discount
    }

@router.get("/{policy_id}/exclusions", response_model=dict)
async def get_policy_exclusions(policy_id: str, db: Session = Depends(get_db)):
    """Get exclusions for a specific policy"""
    policy = db.query(PolicyTerms).filter(PolicyTerms.policy_id == policy_id).first()
    
    if not policy:
        raise HTTPException(status_code=404, detail="Policy terms not found")
    
    return {
        "exclusions": policy.exclusions,
        "covered_services": policy.covered_services,
        "network_providers": policy.network_providers
    }
