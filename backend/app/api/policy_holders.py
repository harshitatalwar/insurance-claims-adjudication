"""
PolicyHolder API - CRUD operations for Insureho policy holders
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from app.schemas import PolicyHolderCreate, PolicyHolderResponse
from app.models import PolicyHolder
from app.utils.database import get_db

router = APIRouter()

@router.post("/", response_model=PolicyHolderResponse, status_code=201)
async def create_policy_holder(
    policy_holder: PolicyHolderCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new policy holder
    
    Policy holder ID is auto-generated in format: PH000001, PH000002, etc.
    """
    try:
        # Generate policy holder ID if not provided
        if not policy_holder.policy_holder_id:
            # Get all policy holders with PH prefix and find the max number
            all_holders = db.query(PolicyHolder).filter(
                PolicyHolder.policy_holder_id.like("PH%")
            ).all()
            
            max_number = 0
            for holder in all_holders:
                try:
                    # Extract number from PH000001 format
                    if holder.policy_holder_id.startswith("PH") and len(holder.policy_holder_id) > 2:
                        number = int(holder.policy_holder_id[2:])
                        max_number = max(max_number, number)
                except (ValueError, IndexError):
                    continue
            
            next_number = max_number + 1
            generated_id = f"PH{next_number:06d}"  # Format: PH000001
        else:
            generated_id = policy_holder.policy_holder_id
        
        # Check if policy holder already exists
        existing = db.query(PolicyHolder).filter(
            PolicyHolder.policy_holder_id == generated_id
        ).first()
        
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Policy holder with ID {generated_id} already exists"
            )
        
        # Parse date strings to datetime objects
        join_date = datetime.utcnow()
        if policy_holder.join_date:
            try:
                join_date = datetime.fromisoformat(policy_holder.join_date.replace('Z', '+00:00'))
            except:
                join_date = datetime.utcnow()
        
        policy_start_date = datetime.utcnow()
        if policy_holder.policy_start_date:
            try:
                policy_start_date = datetime.fromisoformat(policy_holder.policy_start_date.replace('Z', '+00:00'))
            except:
                policy_start_date = datetime.utcnow()
        
        db_policy_holder = PolicyHolder(
            policy_holder_id=generated_id,
            policy_holder_name=policy_holder.policy_holder_name,
            dob=policy_holder.date_of_birth,
            email=policy_holder.email,
            phone=policy_holder.phone,
            join_date=join_date,
            policy_terms_id=policy_holder.policy_terms_id,  # Allow NULL, no default
            policy_start_date=policy_start_date,
            waiting_period_completed=policy_holder.waiting_period_completed if policy_holder.waiting_period_completed is not None else False,
            annual_limit=policy_holder.annual_limit if policy_holder.annual_limit is not None else 50000.0,
            annual_limit_used=policy_holder.annual_limit_used if policy_holder.annual_limit_used is not None else 0.0,
            pre_existing_conditions=policy_holder.pre_existing_conditions or [],
            created_at=datetime.utcnow()
        )
        db.add(db_policy_holder)
        db.commit()
        db.refresh(db_policy_holder)
        return db_policy_holder
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ ERROR creating policy holder: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error creating policy holder: {str(e)}"
        )

@router.get("/", response_model=List[PolicyHolderResponse])
async def list_policy_holders(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """List all policy holders"""
    policy_holders = db.query(PolicyHolder).offset(skip).limit(limit).all()
    return policy_holders

@router.get("/{policy_holder_id}", response_model=PolicyHolderResponse)
async def get_policy_holder(policy_holder_id: str, db: Session = Depends(get_db)):
    """Get a specific policy holder by ID"""
    policy_holder = db.query(PolicyHolder).filter(
        PolicyHolder.policy_holder_id == policy_holder_id
    ).first()
    
    if not policy_holder:
        raise HTTPException(status_code=404, detail="Policy holder not found")
    
    return policy_holder

@router.put("/{policy_holder_id}", response_model=PolicyHolderResponse)
async def update_policy_holder(
    policy_holder_id: str,
    policy_holder_update: PolicyHolderCreate,
    db: Session = Depends(get_db)
):
    """Update a policy holder"""
    db_policy_holder = db.query(PolicyHolder).filter(
        PolicyHolder.policy_holder_id == policy_holder_id
    ).first()
    
    if not db_policy_holder:
        raise HTTPException(status_code=404, detail="Policy holder not found")
    
    db_policy_holder.policy_holder_name = policy_holder_update.policy_holder_name
    db_policy_holder.join_date = policy_holder_update.join_date
    db_policy_holder.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(db_policy_holder)
    return db_policy_holder

@router.delete("/{policy_holder_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_policy_holder(policy_holder_id: str, db: Session = Depends(get_db)):
    """Delete a policy holder"""
    policy_holder = db.query(PolicyHolder).filter(
        PolicyHolder.policy_holder_id == policy_holder_id
    ).first()
    
    if not policy_holder:
        raise HTTPException(status_code=404, detail="Policy holder not found")
    
    db.delete(policy_holder)
    db.commit()
    return None
