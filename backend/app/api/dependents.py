"""
Dependents API - Manage family members under a policy holder
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
import uuid

from app.schemas import DependentCreate, DependentResponse
from app.models import Dependent, PolicyHolder
from app.utils.database import get_db

router = APIRouter()

@router.post("/", response_model=DependentResponse, status_code=status.HTTP_201_CREATED)
async def create_dependent(
    policy_holder_id: str,
    dependent: DependentCreate,
    db: Session = Depends(get_db)
):
    """Add a dependent to a policy holder"""
    # Verify policy holder exists
    policy_holder = db.query(PolicyHolder).filter(
        PolicyHolder.policy_holder_id == policy_holder_id
    ).first()
    
    if not policy_holder:
        raise HTTPException(status_code=404, detail="Policy holder not found")
    
    # Generate auto-increment dependent ID
    last_dependent = db.query(Dependent).order_by(Dependent.id.desc()).first()
    
    if last_dependent and last_dependent.dependent_id.startswith("DEP"):
        try:
            last_number = int(last_dependent.dependent_id[3:])
            next_number = last_number + 1
        except ValueError:
            next_number = 1
    else:
        next_number = 1
    
    dependent_id = f"DEP{next_number:06d}"  # Format: DEP000001
    
    db_dependent = Dependent(
        dependent_id=dependent_id,
        policy_holder_id=policy_holder_id,
        dependent_name=dependent.dependent_name,
        relationship_type=dependent.relationship_type,
        date_of_birth=dependent.date_of_birth,
        gender=dependent.gender,
        created_at=datetime.utcnow()
    )
    
    db.add(db_dependent)
    db.commit()
    db.refresh(db_dependent)
    return db_dependent

@router.get("/", response_model=List[DependentResponse])
async def list_dependents(policy_holder_id: str, db: Session = Depends(get_db)):
    """List all dependents for a policy holder"""
    dependents = db.query(Dependent).filter(
        Dependent.policy_holder_id == policy_holder_id
    ).all()
    return dependents

@router.get("/{dependent_id}", response_model=DependentResponse)
async def get_dependent(dependent_id: str, db: Session = Depends(get_db)):
    """Get a specific dependent"""
    dependent = db.query(Dependent).filter(
        Dependent.dependent_id == dependent_id
    ).first()
    
    if not dependent:
        raise HTTPException(status_code=404, detail="Dependent not found")
    
    return dependent

@router.delete("/{dependent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_dependent(dependent_id: str, db: Session = Depends(get_db)):
    """Remove a dependent"""
    dependent = db.query(Dependent).filter(
        Dependent.dependent_id == dependent_id
    ).first()
    
    if not dependent:
        raise HTTPException(status_code=404, detail="Dependent not found")
    
    db.delete(dependent)
    db.commit()
    return None
