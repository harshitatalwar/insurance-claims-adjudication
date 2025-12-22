"""
Claims Adjudication API
Endpoints for automated claim decision-making
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import logging
from datetime import datetime

from app.models.models import ClaimDecision, Claim, PolicyHolder, Document, DecisionType
from app.schemas.schemas import ClaimDecisionResponse, AdjudicationRequest, ManualReviewOverride
from app.services.adjudication_engine import AdjudicationEngine
from app.utils.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/adjudication", tags=["Adjudication"])


@router.post("/claims/{claim_id}/adjudicate", response_model=ClaimDecisionResponse)
async def adjudicate_claim(
    claim_id: str,
    db: Session = Depends(get_db)
):
    """
    Trigger automated adjudication for a claim
    
    This endpoint:
    1. Retrieves claim and extracted OCR data
    2. Runs through 5-step validation
    3. Makes APPROVED/REJECTED/PARTIAL/MANUAL_REVIEW decision
    4. Saves decision to database
    5. Returns detailed decision with reasoning
    """
    try:
        logger.info(f"📋 Adjudication requested for claim {claim_id}")
        
        # Get claim
        claim = db.query(Claim).filter(Claim.claim_id == claim_id).first()
        if not claim:
            raise HTTPException(status_code=404, detail=f"Claim {claim_id} not found")
        
        # Get policy holder
        policy_holder = db.query(PolicyHolder).filter(
            PolicyHolder.policy_holder_id == claim.policy_holder_id
        ).first()
        if not policy_holder:
            raise HTTPException(status_code=404, detail="Policy holder not found")
        
        # Get extracted data from documents
        documents = db.query(Document).filter(Document.claim_id == claim_id).all()
        if not documents:
            raise HTTPException(status_code=400, detail="No documents found for claim")
        
        # Combine extracted data from all documents
        extracted_data = {}
        for doc in documents:
            if doc.extracted_data:
                extracted_data.update(doc.extracted_data)
        
        if not extracted_data:
            raise HTTPException(status_code=400, detail="No extracted data available. Please process documents first.")
        
        # Add claim amount
        extracted_data["total_amount"] = claim.claimed_amount
        extracted_data["treatment_type"] = claim.treatment_type or "consultation"
        
        # Prepare policy holder data
        policy_holder_data = {
            "policy_holder_id": policy_holder.policy_holder_id,
            "policy_status": policy_holder.policy_status,
            "policy_start_date": policy_holder.policy_start_date.isoformat() if policy_holder.policy_start_date else None,
            "annual_limit": policy_holder.annual_limit,
            "annual_limit_used": policy_holder.annual_limit_used,
            "waiting_period_completed": policy_holder.waiting_period_completed
        }
        
        # Run adjudication
        engine = AdjudicationEngine()
        decision = await engine.adjudicate_claim(claim_id, extracted_data, policy_holder_data)
        
        # Check if decision already exists
        existing_decision = db.query(ClaimDecision).filter(
            ClaimDecision.claim_id == claim_id
        ).first()
        
        if existing_decision:
            # Update existing decision
            for key, value in decision.__dict__.items():
                if not key.startswith('_'):
                    setattr(existing_decision, key, value)
            db.commit()
            db.refresh(existing_decision)
            logger.info(f"✅ Updated decision for claim {claim_id}: {existing_decision.decision}")
            return existing_decision
        else:
            # Save new decision
            db.add(decision)
            db.commit()
            db.refresh(decision)
            
            # Update claim status
            claim.status = decision.decision.value.lower()
            claim.decision = decision.decision
            claim.approved_amount = decision.approved_amount
            claim.confidence_score = decision.confidence_score
            claim.rejection_reasons = decision.rejection_reasons
            claim.notes = decision.notes
            claim.next_steps = decision.next_steps
            db.commit()
            
            logger.info(f"✅ Adjudication complete for claim {claim_id}: {decision.decision}")
            return decision
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Adjudication failed for claim {claim_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Adjudication failed: {str(e)}")


@router.get("/claims/{claim_id}/decision", response_model=ClaimDecisionResponse)
async def get_decision(
    claim_id: str,
    db: Session = Depends(get_db)
):
    """
    Get adjudication decision for a claim
    
    Returns:
        Full decision with reasoning, validation results, and next steps
    """
    decision = db.query(ClaimDecision).filter(ClaimDecision.claim_id == claim_id).first()
    
    if not decision:
        raise HTTPException(
            status_code=404,
            detail=f"No decision found for claim {claim_id}. Please run adjudication first."
        )
    
    return decision


@router.get("/claims/pending-review", response_model=List[ClaimDecisionResponse])
async def get_pending_reviews(
    db: Session = Depends(get_db),
    limit: int = 50
):
    """
    Get all claims requiring manual review
    
    Returns:
        List of claims with MANUAL_REVIEW decision
    """
    decisions = db.query(ClaimDecision).filter(
        ClaimDecision.decision == DecisionType.MANUAL_REVIEW,
        ClaimDecision.reviewed_by == None
    ).limit(limit).all()
    
    logger.info(f"📋 Found {len(decisions)} claims pending manual review")
    return decisions


@router.post("/claims/{claim_id}/decision/override", response_model=ClaimDecisionResponse)
async def override_decision(
    claim_id: str,
    override: ManualReviewOverride,
    db: Session = Depends(get_db)
):
    """
    Human reviewer overrides automated decision
    
    Requires:
        - reviewer_id: ID of the reviewer
        - new_decision: APPROVED/REJECTED/PARTIAL
        - review_notes: Explanation for override
        - reason: Reason for manual intervention
    """
    decision = db.query(ClaimDecision).filter(ClaimDecision.claim_id == claim_id).first()
    
    if not decision:
        raise HTTPException(status_code=404, detail=f"No decision found for claim {claim_id}")
    
    # Update decision with manual override
    decision.decision = override.new_decision
    decision.reviewed_by = override.reviewer_id
    decision.reviewed_at = datetime.utcnow()
    decision.review_notes = override.review_notes
    
    if override.approved_amount is not None:
        decision.approved_amount = override.approved_amount
    
    # Update claim
    claim = db.query(Claim).filter(Claim.claim_id == claim_id).first()
    if claim:
        claim.status = override.new_decision.value.lower()
        claim.decision = override.new_decision
        claim.approved_amount = decision.approved_amount
        claim.notes = f"Manual override by {override.reviewer_id}: {override.review_notes}"
    
    db.commit()
    db.refresh(decision)
    
    logger.info(f"✅ Decision overridden for claim {claim_id} by {override.reviewer_id}")
    return decision


@router.get("/stats/decisions")
async def get_decision_stats(db: Session = Depends(get_db)):
    """
    Get adjudication statistics
    
    Returns:
        - Total decisions
        - Breakdown by decision type
        - Average confidence score
        - Pending manual reviews
    """
    from sqlalchemy import func
    
    total = db.query(func.count(ClaimDecision.id)).scalar()
    
    approved = db.query(func.count(ClaimDecision.id)).filter(
        ClaimDecision.decision == DecisionType.APPROVED
    ).scalar()
    
    rejected = db.query(func.count(ClaimDecision.id)).filter(
        ClaimDecision.decision == DecisionType.REJECTED
    ).scalar()
    
    manual_review = db.query(func.count(ClaimDecision.id)).filter(
        ClaimDecision.decision == DecisionType.MANUAL_REVIEW
    ).scalar()
    
    avg_confidence = db.query(func.avg(ClaimDecision.confidence_score)).scalar()
    
    return {
        "total_decisions": total or 0,
        "approved": approved or 0,
        "rejected": rejected or 0,
        "manual_review": manual_review or 0,
        "pending_review": db.query(func.count(ClaimDecision.id)).filter(
            ClaimDecision.decision == DecisionType.MANUAL_REVIEW,
            ClaimDecision.reviewed_by == None
        ).scalar() or 0,
        "average_confidence": float(avg_confidence) if avg_confidence else 0.0,
        "approval_rate": (approved / total * 100) if total > 0 else 0.0
    }
