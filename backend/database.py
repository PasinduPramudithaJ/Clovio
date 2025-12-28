from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError
import os
from dotenv import load_dotenv

load_dotenv()

# Get database URL from environment
# Default to SQLite for development if PostgreSQL is not available
USE_SQLITE = os.getenv("USE_SQLITE", "false").lower() == "true"
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./clovio.db" if USE_SQLITE else "postgresql://clovio_user:clovio_pass@localhost:5432/clovio_db"
)

def test_postgresql_connection(db_url: str) -> bool:
    """Test if PostgreSQL connection is available."""
    try:
        test_engine = create_engine(db_url, pool_pre_ping=True, connect_args={"connect_timeout": 2})
        with test_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        test_engine.dispose()
        return True
    except Exception:
        return False

# Auto-detect PostgreSQL availability and fallback to SQLite if needed
if not USE_SQLITE and DATABASE_URL.startswith("postgresql"):
    if not test_postgresql_connection(DATABASE_URL):
        print("[WARNING] PostgreSQL connection failed. Falling back to SQLite for development.")
        print("[INFO] To use PostgreSQL, ensure it's running or set USE_SQLITE=false after starting PostgreSQL.")
        DATABASE_URL = "sqlite:///./clovio.db"
        USE_SQLITE = True


def create_database_if_not_exists():
    """
    Create the database if it doesn't exist.
    For SQLite, this is automatic. For PostgreSQL, tries to create the database.
    """
    # SQLite doesn't need database creation
    if DATABASE_URL.startswith("sqlite"):
        print(f"[INFO] Using SQLite database: {DATABASE_URL}")
        return
    
    try:
        # Parse the database URL to extract components
        from urllib.parse import urlparse
        parsed = urlparse(DATABASE_URL)
        
        # Extract database name (last part of path)
        db_name = parsed.path.lstrip('/')
        
        # First, try to connect to the target database to see if it exists
        try:
            test_engine = create_engine(DATABASE_URL, pool_pre_ping=True)
            with test_engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            print(f"[INFO] Database '{db_name}' already exists and is accessible")
            test_engine.dispose()
            return  # Database exists, no need to create
        except Exception:
            # Database doesn't exist, try to create it
            pass
        
        # Create connection URL without database name (connect to default 'postgres' database)
        # Try multiple common default databases
        default_dbs = ['postgres', 'template1']
        admin_engine = None
        
        for default_db in default_dbs:
            try:
                admin_url = f"{parsed.scheme}://{parsed.netloc}/{default_db}"
                admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT", pool_pre_ping=True)
                with admin_engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
                # Connection successful, use this
                break
            except Exception:
                admin_engine = None
                continue
        
        if admin_engine is None:
            raise Exception("Could not connect to PostgreSQL server with any default database")
        
        # Try to create the database
        with admin_engine.connect() as conn:
            # Check if database exists (using parameterized query)
            # Note: Database names can't be parameterized in PostgreSQL, so we validate the name first
            if not db_name or not db_name.replace('_', '').replace('-', '').isalnum():
                raise ValueError(f"Invalid database name: {db_name}")
            
            result = conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :db_name"),
                {"db_name": db_name}
            )
            exists = result.fetchone()
            
            if not exists:
                # Create database (database name is validated, so safe to use in SQL)
                # PostgreSQL requires database names to be quoted if they contain special chars
                safe_db_name = db_name.replace('"', '""')  # Escape quotes
                conn.execute(text(f'CREATE DATABASE "{safe_db_name}"'))
                print(f"[OK] Created database: {db_name}")
            else:
                print(f"[INFO] Database '{db_name}' already exists")
        
        admin_engine.dispose()
        
    except Exception as e:
        # If PostgreSQL is not available, this is handled by auto-fallback above
        # Just log the warning
        print(f"[WARNING] Could not connect to PostgreSQL: {e}")
        print(f"[INFO] Using SQLite fallback for development.")
        print(f"[INFO] To use PostgreSQL, start it using: .\\start_postgres.ps1 or docker-compose up db")


# Create database if it doesn't exist (only for PostgreSQL)
if not USE_SQLITE:
    create_database_if_not_exists()

# Create engine for the application database
# SQLite needs different connection args
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},  # SQLite specific
        pool_pre_ping=False
    )
    print(f"[INFO] Using SQLite database: {DATABASE_URL}")
else:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    print(f"[INFO] Using PostgreSQL database")

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
