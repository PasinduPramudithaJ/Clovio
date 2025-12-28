"""
Database initialization script.
Creates the database if it doesn't exist, then creates all tables.
Run this script to set up your database.
"""
from database import engine, Base, create_database_if_not_exists
from models import User, Skill, Project, ProjectMember, Task, Document, ChatMessage, Contribution, LearningAnalytics

if __name__ == "__main__":
    print("=" * 60)
    print("Clovio Database Initialization")
    print("=" * 60)
    
    # Create database if it doesn't exist
    print("\n[1/2] Checking database...")
    create_database_if_not_exists()
    
    # Create all tables
    print("\n[2/2] Creating database tables...")
    try:
        Base.metadata.create_all(bind=engine)
        print("[OK] All database tables created successfully!")
        print("\nDatabase initialization complete!")
        print("=" * 60)
    except Exception as e:
        print(f"[ERROR] Failed to create tables: {e}")
        print("\nPlease check:")
        print("  1. PostgreSQL is running")
        print("  2. Database credentials are correct in .env file")
        print("  3. User has CREATE privileges")
        print("=" * 60)
