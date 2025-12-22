from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.schemas import ManualReviewCreate, ManualReviewUpdate
from app.models import ManualReview, Claim
from app.utils.database import get_db

router = APIRouter()

@router.get("/reviews/pending")
async def get_pending_reviews(db: Session = Depends(get_db)):
    """Get all claims pending manual review"""
    reviews = db.query(ManualReview).filter(
        ManualReview.review_status == "PENDING"
    ).all()
    return reviews

@router.post("/reviews", status_code=201)
async def create_manual_review(review: ManualReviewCreate, db: Session = Depends(get_db)):
    """Create a manual review request"""
    claim = db.query(Claim).filter(Claim.claim_id == review.claim_id).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    
    db_review = ManualReview(
        claim_id=review.claim_id,
        original_decision=claim.decision,
        review_notes=review.review_notes
    )
    db.add(db_review)
    db.commit()
    db.refresh(db_review)
    
    return db_review

@router.put("/reviews/{review_id}")
async def update_review(
    review_id: int,
    review_update: ManualReviewUpdate,
    db: Session = Depends(get_db)
):
    """Update a manual review"""
    review = db.query(ManualReview).filter(ManualReview.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    
    review.reviewer_id = review_update.reviewer_id
    review.review_status = review_update.review_status
    review.review_notes = review_update.review_notes
    review.final_decision = review_update.final_decision
    
    db.commit()
    db.refresh(review)
    
    return review

@router.get("/analytics")
async def get_analytics(db: Session = Depends(get_db)):
    """Get system analytics"""
    from sqlalchemy import func
    
    total_claims = db.query(func.count(Claim.id)).scalar()
    approved_claims = db.query(func.count(Claim.id)).filter(
        Claim.decision == "APPROVED"
    ).scalar()
    rejected_claims = db.query(func.count(Claim.id)).filter(
        Claim.decision == "REJECTED"
    ).scalar()
    pending_reviews = db.query(func.count(ManualReview.id)).filter(
        ManualReview.review_status == "PENDING"
    ).scalar()
    
    avg_confidence = db.query(func.avg(Claim.confidence_score)).scalar()
    
    return {
        "total_claims": total_claims,
        "approved_claims": approved_claims,
        "rejected_claims": rejected_claims,
        "pending_reviews": pending_reviews,
        "average_confidence": float(avg_confidence) if avg_confidence else 0.0,
        "approval_rate": (approved_claims / total_claims * 100) if total_claims > 0 else 0.0
    }
