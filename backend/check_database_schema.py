"""
Check and fix database schema for new columns.
Run this script to ensure all database columns exist.
"""
from database import engine, Base
from models import Meeting
from sqlalchemy import inspect, text

def check_and_fix_schema():
    """Check if meeting_room_url column exists, add it if missing."""
    inspector = inspect(engine)
    
    # Check if meetings table exists
    if 'meetings' not in inspector.get_table_names():
        print("[INFO] Meetings table doesn't exist. Creating all tables...")
        Base.metadata.create_all(bind=engine)
        print("[OK] All tables created")
        return
    
    # Check if meeting_room_url column exists
    columns = [col['name'] for col in inspector.get_columns('meetings')]
    
    if 'meeting_room_url' not in columns:
        print("[INFO] meeting_room_url column missing. Adding it...")
        try:
            with engine.connect() as conn:
                # Try PostgreSQL first
                try:
                    conn.execute(text("ALTER TABLE meetings ADD COLUMN meeting_room_url VARCHAR(500)"))
                    conn.commit()
                    print("[OK] Column added successfully (PostgreSQL)")
                except Exception as e:
                    # Try SQLite syntax
                    if 'syntax error' in str(e).lower() or 'near' in str(e).lower():
                        print("[INFO] Trying SQLite syntax...")
                        conn.execute(text("ALTER TABLE meetings ADD COLUMN meeting_room_url VARCHAR(500)"))
                        conn.commit()
                        print("[OK] Column added successfully (SQLite)")
                    else:
                        raise
        except Exception as e:
            print(f"[ERROR] Failed to add column: {e}")
            print("[INFO] You may need to run the migration manually or recreate the database")
    else:
        print("[OK] meeting_room_url column already exists")

if __name__ == "__main__":
    print("=" * 60)
    print("Database Schema Check")
    print("=" * 60)
    check_and_fix_schema()
    print("=" * 60)

