"""
Atomic ID Generation using PostgreSQL Sequences

This module provides thread-safe, race-condition-free ID generation
for Claims, Policy Holders, and Documents using PostgreSQL sequences.

Benefits:
- O(1) performance (no table scans)
- Atomic operations (no race conditions)
- Scalable to millions of records
- Database-level guarantees
"""
from sqlalchemy.orm import Session
from sqlalchemy import text


def generate_claim_id(db: Session) -> str:
    """
    Generate next claim ID using PostgreSQL sequence
    
    Format: CLM000001, CLM000002, ...
    
    Thread-safe and race-condition-free.
    O(1) performance - no table scans.
    
    Args:
        db: Database session
        
    Returns:
        Next claim ID in format CLMxxxxxx
    """
    result = db.execute(text("SELECT nextval('claim_id_seq')"))
    next_id = result.scalar()
    return f"CLM{next_id:06d}"


def generate_policy_holder_id(db: Session) -> str:
    """
    Generate next policy holder ID using PostgreSQL sequence
    
    Format: PH000001, PH000002, ...
    
    Thread-safe and race-condition-free.
    O(1) performance - no table scans.
    
    Args:
        db: Database session
        
    Returns:
        Next policy holder ID in format PHxxxxxx
    """
    result = db.execute(text("SELECT nextval('policy_holder_id_seq')"))
    next_id = result.scalar()
    return f"PH{next_id:06d}"


def generate_document_id(db: Session) -> str:
    """
    Generate next document ID using PostgreSQL sequence
    
    Format: DOC000001, DOC000002, ...
    
    Note: Currently documents use UUIDs (DOC + UUID).
    This function is provided for future use if sequential IDs are needed.
    
    Thread-safe and race-condition-free.
    O(1) performance - no table scans.
    
    Args:
        db: Database session
        
    Returns:
        Next document ID in format DOCxxxxxx
    """
    result = db.execute(text("SELECT nextval('document_id_seq')"))
    next_id = result.scalar()
    return f"DOC{next_id:06d}"


def get_current_claim_sequence(db: Session) -> int:
    """Get current value of claim_id_seq without incrementing"""
    result = db.execute(text("SELECT currval('claim_id_seq')"))
    return result.scalar()


def get_current_policy_holder_sequence(db: Session) -> int:
    """Get current value of policy_holder_id_seq without incrementing"""
    result = db.execute(text("SELECT currval('policy_holder_id_seq')"))
    return result.scalar()


def reset_claim_sequence(db: Session, value: int = 1):
    """
    Reset claim_id_seq to specific value
    
    WARNING: Use only for testing or data migration
    """
    db.execute(text(f"SELECT setval('claim_id_seq', {value}, false)"))
    db.commit()


def reset_policy_holder_sequence(db: Session, value: int = 1):
    """
    Reset policy_holder_id_seq to specific value
    
    WARNING: Use only for testing or data migration
    """
    db.execute(text(f"SELECT setval('policy_holder_id_seq', {value}, false)"))
    db.commit()
