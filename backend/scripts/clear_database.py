"""
TRUNCATE all tables - Simple and effective approach
WARNING: This will delete ALL data! Use with caution.
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy import text, inspect
from app.utils.database import SessionLocal, engine

def truncate_all_tables():
    """Truncate all tables (fastest way to clear data)"""
    db = SessionLocal()
    
    try:
        print("⚠️  WARNING: This will delete ALL data from the database!")
        print("="*60)
        
        # Confirm
        confirm = input("Type 'DELETE ALL' to confirm: ")
        if confirm != "DELETE ALL":
            print("\nCancelled. No data was deleted.")
            return
        
        print("\nDiscovering tables...")
        
        # Get all table names
        inspector = inspect(engine)
        all_tables = inspector.get_table_names()
        
        # Exclude alembic_version (migration history)
        tables_to_clear = [t for t in all_tables if t != 'alembic_version']
        
        print(f"Found {len(tables_to_clear)} tables to clear:")
        for table in tables_to_clear:
            print(f"  - {table}")
        
        print("\nClearing tables using TRUNCATE CASCADE...")
        
        deleted_counts = {}
        total_deleted = 0
        
        for table in tables_to_clear:
            try:
                # Get count before truncation
                count_result = db.execute(text(f'SELECT COUNT(*) FROM "{table}"'))
                count = count_result.scalar()
                
                if count > 0:
                    # TRUNCATE with CASCADE removes all data and resets sequences
                    # CASCADE automatically handles foreign key constraints
                    db.execute(text(f'TRUNCATE TABLE "{table}" RESTART IDENTITY CASCADE'))
                    db.commit()
                    deleted_counts[table] = count
                    total_deleted += count
                    print(f"✓ Cleared {count} records from {table}")
                else:
                    print(f"  {table} was already empty")
                    
            except Exception as e:
                error_msg = str(e)[:200]
                print(f"⚠️  Could not clear {table}: {error_msg}")
                db.rollback()
        
        print("\n" + "="*60)
        print("✅ Database clearing completed!")
        print("="*60)
        print(f"\nTotal records deleted: {total_deleted}")
        
        if deleted_counts:
            print("\n📊 Breakdown:")
            for table, count in sorted(deleted_counts.items()):
                print(f"  - {table}: {count} records")
        
        # Verify tables are empty
        print("\n🔍 Verifying all tables are empty...")
        all_empty = True
        
        for table in tables_to_clear:
            try:
                count_result = db.execute(text(f'SELECT COUNT(*) FROM "{table}"'))
                count = count_result.scalar()
                if count > 0:
                    print(f"  ⚠️  {table}: still has {count} records!")
                    all_empty = False
            except:
                pass
        
        if all_empty:
            print("  ✅ All tables are empty! Database is clean.")
        else:
            print("  ⚠️  Some tables still have data.")
        
        print("\n🎯 Next steps:")
        print("1. Refresh DBeaver (F5) to see changes")
        print("2. Go to http://localhost:3000/register")
        print("3. Create new users - you set the passwords!")
        print("\n💡 First user will get:")
        print("  - policy_holder_id: PH000001")
        print("  - annual_limit: ₹50,000")
        print("  - Password: whatever you set!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    truncate_all_tables()
