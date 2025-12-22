from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
import uuid

from app.schemas import ClaimCreate, ClaimResponse, AdjudicationResult
from app.models import Claim, DecisionType
from app.utils.database import get_db
# DecisionEngine removed - using unified AdjudicationEngine instead

# SSE imports
from sse_starlette.sse import EventSourceResponse
from fastapi import Request
import asyncio
import redis
import os
import json
import logging

logger = logging.getLogger(__name__)
import redis
import os
import json

router = APIRouter()

@router.post("/", response_model=ClaimResponse, status_code=status.HTTP_201_CREATED)
async def create_claim(claim: ClaimCreate, db: Session = Depends(get_db)):
    """Create a new claim"""
    # Import PolicyHolder here to avoid circular imports
    from app.models import PolicyHolder
    
    # Validate policy holder exists
    policy_holder = db.query(PolicyHolder).filter(
        PolicyHolder.policy_holder_id == claim.policy_holder_id
    ).first()
    
    if not policy_holder:
        raise HTTPException(
            status_code=404,
            detail=f"Policy holder {claim.policy_holder_id} not found. Please create the policy holder first."
        )
    
    # Generate claim ID using atomic PostgreSQL sequence
    # This is O(1), thread-safe, and prevents race conditions
    from app.utils.id_generator import generate_claim_id
    claim_id = generate_claim_id(db)
    
    db_claim = Claim(
        claim_id=claim_id,
        policy_holder_id=claim.policy_holder_id,
        policy_holder_name=policy_holder.policy_holder_name,
        treatment_date=claim.treatment_date or datetime.utcnow(),
        treatment_type=claim.treatment_type,
        treatment_category=claim.treatment_type,  # Same as type for now
        claimed_amount=claim.claimed_amount,
        provider_name=claim.provider_name,
        provider_network=claim.provider_network or False,
        doctor_name=claim.doctor_name,
        doctor_registration_number=claim.doctor_registration_number,
        diagnosis=claim.diagnosis,
        submission_date=datetime.utcnow(),
        status="pending"
    )
    db.add(db_claim)
    db.commit()
    db.refresh(db_claim)
    return db_claim

@router.get("/", response_model=List[ClaimResponse])
async def list_claims(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """List all claims"""
    claims = db.query(Claim).offset(skip).limit(limit).all()
    return claims

@router.get("/{claim_id}", response_model=ClaimResponse)
async def get_claim(claim_id: str, db: Session = Depends(get_db)):
    """Get a specific claim by ID"""
    claim = db.query(Claim).filter(Claim.claim_id == claim_id).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    return claim

@router.post("/{claim_id}/adjudicate", response_model=AdjudicationResult)
async def adjudicate_claim(claim_id: str, db: Session = Depends(get_db)):
    """
    Trigger adjudication for a claim
    
    Uses the unified AdjudicationEngine (same as Celery worker)
    to ensure consistent adjudication logic
    """
    claim = db.query(Claim).filter(Claim.claim_id == claim_id).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    
    # Get policy holder
    policy_holder = db.query(PolicyHolder).filter(
        PolicyHolder.policy_holder_id == claim.policy_holder_id
    ).first()
    if not policy_holder:
        raise HTTPException(status_code=404, detail="Policy holder not found")
    
    # Get documents for this claim
    documents = db.query(Document).filter(Document.claim_id == claim_id).all()
    if not documents:
        raise HTTPException(status_code=400, detail="No documents found for claim")
    
    # Combine extracted data from all documents
    extracted_data = {}
    for doc in documents:
        if doc.extracted_data:
            extracted_data.update(doc.extracted_data)
    
    if not extracted_data:
        raise HTTPException(status_code=400, detail="No extracted data available")
    
    # Update status to processing
    claim.status = "processing"
    db.commit()
    
    # Initialize unified adjudication engine
    from app.services.adjudication_engine import AdjudicationEngine
    engine = AdjudicationEngine()
    
    # Build comprehensive policy context (runtime only)
    policy_context = {
        "policy_holder_id": policy_holder.policy_holder_id,
        "policy_holder_name": policy_holder.policy_holder_name,
        "dob": policy_holder.dob,
        "policy_status": policy_holder.policy_status.value if hasattr(policy_holder.policy_status, 'value') else str(policy_holder.policy_status),
        "policy_start_date": policy_holder.policy_start_date.isoformat() if policy_holder.policy_start_date else None,
        "join_date": policy_holder.join_date.isoformat() if policy_holder.join_date else None,
        "annual_limit": policy_holder.annual_limit,
        "annual_limit_used": policy_holder.annual_limit_used,
        "annual_limit_remaining": policy_holder.annual_limit - policy_holder.annual_limit_used,
        "waiting_period_completed": policy_holder.waiting_period_completed,
        "pre_existing_conditions": policy_holder.pre_existing_conditions or []
    }
    
    # Build adjudication context (same as worker)
    adjudication_context = {
        "policy_context": policy_context,
        "claim_evidence": extracted_data,
        "policy_terms": engine.policy_terms
    }
    
    # Run adjudication using unified engine
    decision = await engine.adjudicate_claim(claim_id, adjudication_context)
    
    # Update claim with decision
    claim.decision = decision.decision
    claim.approved_amount = decision.approved_amount
    claim.eligible_amount = decision.original_amount
    claim.co_payment_amount = decision.copay_amount
    claim.copay_percentage = decision.copay_percentage
    claim.confidence_score = decision.confidence_score
    claim.rejection_reasons = decision.rejection_reasons
    claim.notes = decision.notes
    claim.next_steps = decision.next_steps
    
    # Update status based on decision
    if decision.decision == DecisionType.APPROVED:
        claim.status = "approved"
        # Update policy holder's annual limit used
        policy_holder.annual_limit_used += decision.approved_amount
    elif decision.decision == DecisionType.REJECTED:
        claim.status = "rejected"
    elif decision.decision == DecisionType.MANUAL_REVIEW:
        claim.status = "under_review"
    
    # Set processed timestamp
    claim.processed_at = datetime.utcnow()
    
    db.commit()
    db.refresh(claim)
    
    # Convert ClaimDecision to AdjudicationResult for API response
    return AdjudicationResult(
        claim_id=decision.claim_id,
        decision=decision.decision,
        approved_amount=decision.approved_amount,
        rejection_reasons=decision.rejection_reasons,
        confidence_score=decision.confidence_score,
        notes=decision.notes,
        next_steps=decision.next_steps,
        deductions={},
        co_payment_amount=decision.copay_amount,
        eligible_amount=decision.original_amount
    )

@router.delete("/{claim_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_claim(claim_id: str, db: Session = Depends(get_db)):
    """Delete a claim"""
    claim = db.query(Claim).filter(Claim.claim_id == claim_id).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    
    db.delete(claim)
    db.commit()
    return None

@router.get("/{claim_id}/stream")
async def stream_claim_updates(claim_id: str, request: Request):
    """Real-time SSE stream for claim updates"""
    
    async def event_generator():
        # Connect to Redis
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        r = redis.from_url(redis_url, decode_responses=True)
        pubsub = r.pubsub()
        channel = f"claim_updates:{claim_id}"
        pubsub.subscribe(channel)
        
        logger.info(f"🔌 SSE client connected to {channel}")
        
        try:
            # Send initial connection confirmation
            yield {
                "event": "connected",
                "data": json.dumps({"status": "connected", "claim_id": claim_id})
            }
            
            while True:
                # Check if client disconnected
                if await request.is_disconnected():
                    logger.info(f"🔌 SSE client disconnected from {channel}")
                    break
                
                # FIXED: Use listen() with timeout instead of get_message()
                # This properly blocks and waits for messages
                message = pubsub.get_message(timeout=1.0)
                
                if message and message['type'] == 'message':
                    logger.info(f"📨 SSE sending: {message['data']}")
                    yield {
                        "event": "message", 
                        "data": message["data"]
                    }
                
                # Small sleep to prevent CPU spinning
                await asyncio.sleep(0.1)
                
        except Exception as e:
            logger.error(f"❌ SSE error: {e}")
        finally:
            try:
                pubsub.unsubscribe(channel)
                pubsub.close()
                r.close()
                logger.info(f"🔌 SSE connection closed for {channel}")
            except:
                pass

    return EventSourceResponse(event_generator())

