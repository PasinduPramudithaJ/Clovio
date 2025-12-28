from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from database import engine, Base, SessionLocal
import os
from dotenv import load_dotenv
import traceback

# Import routers
from routers import auth, users, projects, tasks, documents, chat, analytics, scheduling, contributions, learning_analytics, assessments, webrtc
from models import User, UserRole
from auth import get_password_hash

load_dotenv()

# Create database tables (this runs after database creation in database.py)
try:
    Base.metadata.create_all(bind=engine)
    print("[OK] Database tables initialized")
    
    # Check and fix schema for new columns (like meeting_room_url)
    try:
        from sqlalchemy import inspect, text
        inspector = inspect(engine)
        if 'meetings' in inspector.get_table_names():
            columns = [col['name'] for col in inspector.get_columns('meetings')]
            if 'meeting_room_url' not in columns:
                print("[INFO] Adding meeting_room_url column to meetings table...")
                with engine.connect() as conn:
                    # Try PostgreSQL syntax first (IF NOT EXISTS)
                    try:
                        conn.execute(text("ALTER TABLE meetings ADD COLUMN IF NOT EXISTS meeting_room_url VARCHAR(500)"))
                        conn.commit()
                        print("[OK] meeting_room_url column added (PostgreSQL)")
                    except Exception:
                        # Fallback to standard SQL (for SQLite and others)
                        try:
                            conn.execute(text("ALTER TABLE meetings ADD COLUMN meeting_room_url VARCHAR(500)"))
                            conn.commit()
                            print("[OK] meeting_room_url column added (SQLite/Standard)")
                        except Exception as e2:
                            # Column might already exist or other error
                            if 'duplicate' in str(e2).lower() or 'already exists' in str(e2).lower():
                                print("[INFO] meeting_room_url column already exists")
                            else:
                                raise
    except Exception as e:
        print(f"[WARNING] Could not check/update schema: {e}")
        print("[INFO] Schema check skipped - tables will be created/updated on next migration")
        
except Exception as e:
    print(f"[ERROR] Failed to create database tables: {e}")
    print("[INFO] Please check your database connection and try again")
    print("[INFO] Tip: Set USE_SQLITE=true in .env file to use SQLite for development")


def create_default_admin():
    """Create default admin account if it doesn't exist."""
    # Default admin credentials (hardcoded)
    ADMIN_EMAIL = "admin@clovio.com"
    ADMIN_PASSWORD = "Admin@12345"  # Change this in production!
    ADMIN_NAME = "System Administrator"
    
    db = SessionLocal()
    try:
        # Check if admin already exists
        admin_user = db.query(User).filter(User.email == ADMIN_EMAIL).first()
        if admin_user:
            print(f"[INFO] Admin account already exists: {ADMIN_EMAIL}")
            return
        
        # Create admin user
        hashed_password = get_password_hash(ADMIN_PASSWORD)
        admin_user = User(
            email=ADMIN_EMAIL,
            hashed_password=hashed_password,
            full_name=ADMIN_NAME,
            role=UserRole.ADMIN,
            is_active=True,
            is_verified=True
        )
        
        db.add(admin_user)
        db.commit()
        print(f"[OK] Default admin account created")
        print(f"[INFO] Admin Email: {ADMIN_EMAIL}")
        print(f"[INFO] Admin Password: {ADMIN_PASSWORD}")
        print(f"[WARNING] Please change the admin password after first login!")
    except Exception as e:
        db.rollback()
        print(f"[WARNING] Failed to create default admin account: {e}")
    finally:
        db.close()


# Create default admin account on startup
try:
    create_default_admin()
except Exception as e:
    print(f"[WARNING] Could not create default admin: {e}")


def authorize_all_users():
    """Authorize all existing users - verify and activate them. Admin users are always authorized."""
    db = SessionLocal()
    try:
        # First, ensure all admin users are always authorized
        admin_users = db.query(User).filter(User.role == UserRole.ADMIN).all()
        admin_updated = 0
        for admin_user in admin_users:
            if not admin_user.is_verified or not admin_user.is_active:
                admin_user.is_verified = True
                admin_user.is_active = True
                admin_updated += 1
        
        # Get all other users that are not verified or not active
        users_to_authorize = db.query(User).filter(
            (User.is_verified == False) | (User.is_active == False)
        ).all()
        
        total_updated = len(users_to_authorize)
        if admin_updated > 0 or total_updated > 0:
            db.commit()
            if admin_updated > 0:
                print(f"[OK] Authorized {admin_updated} admin user(s) (always authorized)")
            if total_updated > 0:
                print(f"[OK] Authorized {total_updated} existing user(s) (verified and activated)")
        else:
            print("[INFO] All users are already authorized")
    except Exception as e:
        db.rollback()
        print(f"[WARNING] Could not authorize existing users: {e}")
    finally:
        db.close()


# Authorize all existing users (verify and activate)
try:
    authorize_all_users()
except Exception as e:
    print(f"[WARNING] Could not authorize users: {e}")

app = FastAPI(
    title="Clovio API",
    description="AI-powered academic collaboration platform",
    version="1.0.0"
)

# CORS middleware - must be added before routers
# Parse CORS origins from environment variable
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173")
# Split and strip whitespace
cors_origins_list = [origin.strip() for origin in cors_origins.split(",") if origin.strip()]

# Add wildcard for development if needed
if not cors_origins_list:
    cors_origins_list = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins_list if "*" not in cors_origins_list else ["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Global exception handler to ensure CORS headers are always sent
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle all exceptions and ensure CORS headers are included."""
    print(f"[ERROR] Unhandled exception: {exc}")
    print(traceback.format_exc())
    
    # Get origin from request
    origin = request.headers.get("origin", "")
    
    # Determine CORS origin
    if "*" in cors_origins_list:
        cors_origin = "*"
    elif origin and origin in cors_origins_list:
        cors_origin = origin
    elif cors_origins_list:
        cors_origin = cors_origins_list[0]
    else:
        cors_origin = origin if origin else "*"
    
    # Don't include credentials header if origin is wildcard
    headers = {
        "Access-Control-Allow-Origin": cors_origin,
        "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, PATCH, OPTIONS",
        "Access-Control-Allow-Headers": "*",
    }
    
    if cors_origin != "*":
        headers["Access-Control-Allow-Credentials"] = "true"
    
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {str(exc)}"},
        headers=headers
    )

# Include routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(projects.router)
app.include_router(tasks.router)
app.include_router(documents.router)
app.include_router(chat.router)
app.include_router(analytics.router)
app.include_router(scheduling.router)
app.include_router(contributions.router)
app.include_router(learning_analytics.router)
app.include_router(assessments.router)
app.include_router(webrtc.router)


@app.get("/")
async def root():
    return {
        "message": "Welcome to Clovio API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

