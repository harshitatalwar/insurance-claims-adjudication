from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Dict, List
from datetime import datetime, timedelta

from app.models import Claim, DecisionType
from app.utils.database import get_db

router = APIRouter()

@router.get("/accuracy")
async def get_accuracy_metrics(db: Session = Depends(get_db)):
    """Get AI accuracy metrics"""
    total_decisions = db.query(func.count(Claim.id)).filter(
        Claim.decision.isnot(None)
    ).scalar()
    
    high_confidence = db.query(func.count(Claim.id)).filter(
        Claim.confidence_score >= 0.8
    ).scalar()
    
    medium_confidence = db.query(func.count(Claim.id)).filter(
        Claim.confidence_score >= 0.5,
        Claim.confidence_score < 0.8
    ).scalar()
    
    low_confidence = db.query(func.count(Claim.id)).filter(
        Claim.confidence_score < 0.5
    ).scalar()
    
    return {
        "total_decisions": total_decisions,
        "high_confidence_count": high_confidence,
        "medium_confidence_count": medium_confidence,
        "low_confidence_count": low_confidence,
        "high_confidence_percentage": (high_confidence / total_decisions * 100) if total_decisions > 0 else 0.0
    }

@router.get("/decision-distribution")
async def get_decision_distribution(db: Session = Depends(get_db)):
    """Get distribution of decision types"""
    decisions = db.query(
        Claim.decision,
        func.count(Claim.id).label('count')
    ).group_by(Claim.decision).all()
    
    return {
        "distribution": [
            {"decision": d.decision, "count": d.count}
            for d in decisions if d.decision
        ]
    }

@router.get("/processing-time")
async def get_processing_time_metrics(db: Session = Depends(get_db)):
    """Get processing time statistics"""
    # This is a placeholder - in production, you'd track actual processing times
    return {
        "average_processing_time_seconds": 3.5,
        "min_processing_time_seconds": 1.2,
        "max_processing_time_seconds": 8.7,
        "median_processing_time_seconds": 3.1
    }

@router.get("/trends")
async def get_trends(days: int = 7, db: Session = Depends(get_db)):
    """Get claim trends over time"""
    start_date = datetime.utcnow() - timedelta(days=days)
    
    daily_claims = db.query(
        func.date(Claim.created_at).label('date'),
        func.count(Claim.id).label('count')
    ).filter(
        Claim.created_at >= start_date
    ).group_by(
        func.date(Claim.created_at)
    ).all()
    
    return {
        "period_days": days,
        "daily_claims": [
            {"date": str(dc.date), "count": dc.count}
            for dc in daily_claims
        ]
    }

@router.get("/confusion-matrix")
async def get_confusion_matrix(db: Session = Depends(get_db)):
    """Get confusion matrix for AI decisions (requires ground truth data)"""
    # Placeholder - in production, you'd compare AI decisions with manual review outcomes
    return {
        "true_positives": 85,
        "true_negatives": 12,
        "false_positives": 2,
        "false_negatives": 1,
        "accuracy": 0.97,
        "precision": 0.977,
        "recall": 0.988,
        "f1_score": 0.982
    }
