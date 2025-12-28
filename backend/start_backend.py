#!/usr/bin/env python3
"""
Startup script for Clovio backend.
Checks dependencies and starts the server with proper error handling.
"""
import os
import sys
import subprocess
from pathlib import Path

def check_postgresql():
    """Check if PostgreSQL is accessible."""
    try:
        from sqlalchemy import create_engine, text
        from dotenv import load_dotenv
        
        load_dotenv()
        db_url = os.getenv(
            "DATABASE_URL",
            "postgresql://clovio_user:clovio_pass@localhost:5432/clovio_db"
        )
        
        if db_url.startswith("sqlite"):
            return True, "SQLite"
        
        engine = create_engine(db_url, pool_pre_ping=True)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        engine.dispose()
        return True, "PostgreSQL"
    except Exception as e:
        return False, str(e)

def suggest_sqlite():
    """Suggest using SQLite if PostgreSQL is not available."""
    env_file = Path(".env")
    env_content = ""
    
    if env_file.exists():
        env_content = env_file.read_text()
    
    if "USE_SQLITE" not in env_content:
        print("\n" + "="*60)
        print("PostgreSQL is not available!")
        print("="*60)
        print("\nQuick fix: Use SQLite for development")
        print("\nAdd this to your .env file:")
        print("USE_SQLITE=true")
        print("\nOr run this command:")
        print('echo USE_SQLITE=true >> .env')
        print("\n" + "="*60 + "\n")
        
        # Ask user if they want to use SQLite
        response = input("Would you like to use SQLite for development? (y/n): ").strip().lower()
        if response == 'y':
            if env_content and not env_content.endswith('\n'):
                env_content += '\n'
            env_content += "USE_SQLITE=true\n"
            env_file.write_text(env_content)
            print("[OK] Updated .env file to use SQLite")
            return True
    
    return False

def main():
    """Main startup function."""
    print("="*60)
    print("Clovio Backend Startup")
    print("="*60)
    
    # Check PostgreSQL
    print("\n[1/3] Checking database connection...")
    pg_available, pg_status = check_postgresql()
    
    if not pg_available:
        print(f"[WARNING] Database not available: {pg_status}")
        if not suggest_sqlite():
            print("\n[ERROR] Cannot start without database.")
            print("Please:")
            print("  1. Start PostgreSQL: .\\start_postgres.ps1")
            print("  2. Or set USE_SQLITE=true in .env file")
            sys.exit(1)
    else:
        print(f"[OK] Database available: {pg_status}")
    
    # Check Python dependencies
    print("\n[2/3] Checking Python dependencies...")
    try:
        import fastapi
        import uvicorn
        import sqlalchemy
        print("[OK] All dependencies installed")
    except ImportError as e:
        print(f"[ERROR] Missing dependency: {e}")
        print("Please run: pip install -r requirements.txt")
        sys.exit(1)
    
    # Start server
    print("\n[3/3] Starting FastAPI server...")
    print("="*60)
    print("Server will be available at: http://localhost:8000")
    print("API docs will be available at: http://localhost:8000/docs")
    print("="*60 + "\n")
    
    try:
        import uvicorn
        uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
    except KeyboardInterrupt:
        print("\n\n[INFO] Server stopped by user")
    except Exception as e:
        print(f"\n[ERROR] Failed to start server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

