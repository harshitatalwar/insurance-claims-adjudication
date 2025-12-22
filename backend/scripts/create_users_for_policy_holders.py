"""
Script to create auth users for existing policy holders
Run this once to migrate existing policy holders to have login credentials
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from app.database import SessionLocal, engine
from app.models import PolicyHolder, User
from app.auth import get_password_hash

def create_users_for_policy_holders():
    """Create auth users for all policy holders that don't have one"""
    db = SessionLocal()
    
    try:
        # Get all policy holders
        policy_holders = db.query(PolicyHolder).all()
        
        print(f"Found {len(policy_holders)} policy holders")
        
        created_count = 0
        skipped_count = 0
        
        for ph in policy_holders:
            # Check if user already exists with this email
            existing_user = db.query(User).filter(User.email == ph.email).first()
            
            if existing_user:
                print(f"✓ User already exists for {ph.email} - skipping")
                skipped_count += 1
                continue
            
            # Create default password (you should change this!)
            default_password = "password123"  # CHANGE THIS!
            
            # Create new user
            new_user = User(
                email=ph.email,
                hashed_password=get_password_hash(default_password),
                full_name=ph.policy_holder_name,
                role="user",
                is_active=True
            )
            
            db.add(new_user)
            db.commit()
            
            print(f"✓ Created user for {ph.email} (Policy ID: {ph.policy_holder_id})")
            print(f"  Default password: {default_password}")
            created_count += 1
        
        print("\n" + "="*50)
        print(f"Summary:")
        print(f"  Created: {created_count} users")
        print(f"  Skipped: {skipped_count} users (already existed)")
        print(f"\nIMPORTANT: Default password is 'password123'")
        print(f"Users should change their password after first login!")
        print("="*50)
        
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    print("Creating auth users for existing policy holders...")
    print("="*50)
    create_users_for_policy_holders()
