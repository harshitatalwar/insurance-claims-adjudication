"""
Add password column to existing policy_holders table
"""
import sys
import os
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.utils.database import SessionLocal

def add_password_column():
    """Add hashed_password and is_active columns to policy_holders"""
    db = SessionLocal()
    
    try:
        print("Adding password columns to policy_holders table...")
        
        # Add hashed_password column
        try:
            db.execute(text('ALTER TABLE policy_holders ADD COLUMN hashed_password VARCHAR'))
            db.commit()
            print("✓ Added hashed_password column")
        except Exception as e:
            if "already exists" in str(e):
                print("  hashed_password column already exists")
                db.rollback()
            else:
                raise
        
        # Add is_active column
        try:
            db.execute(text('ALTER TABLE policy_holders ADD COLUMN is_active BOOLEAN DEFAULT true'))
            db.commit()
            print("✓ Added is_active column")
        except Exception as e:
            if "already exists" in str(e):
                print("  is_active column already exists")
                db.rollback()
            else:
                raise
        
        print("\n✅ Policy holders table updated successfully!")
        print("Now you can use policy_holders for authentication.")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    add_password_column()
