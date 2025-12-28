from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt, ExpiredSignatureError
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from database import get_db
from models import User
from utils import get_or_create_secret_key
import hashlib

# Automatically generate secret key if not set in environment
SECRET_KEY = get_or_create_secret_key()
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

# Increased bcrypt rounds for better security (rounds=14 means 2^14 iterations)
# Higher rounds = more secure but slower hashing
# Note: bcrypt version 4.0.1 is required for compatibility with passlib
try:
    # Configure bcrypt with increased rounds for better security
    pwd_context = CryptContext(
        schemes=["bcrypt"],
        deprecated="auto",
        bcrypt__rounds=14
    )
except (AttributeError, TypeError, ValueError) as e:
    # Fallback to default configuration if bcrypt configuration fails
    # This can happen if bcrypt version is incompatible
    print(f"[WARNING] Could not set bcrypt rounds, using default: {e}")
    print("[INFO] Install bcrypt==4.0.1 for full compatibility: pip install bcrypt==4.0.1")
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")


def _pre_hash_password(password: str) -> str:
    """
    Pre-hash password with SHA256 to handle passwords longer than 72 bytes.
    Bcrypt has a 72-byte limit, so we hash with SHA256 first (always 32 bytes).
    """
    return hashlib.sha256(password.encode('utf-8')).hexdigest()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify password with backward compatibility.
    Tries new method (SHA256 + bcrypt) first, then falls back to old method (direct bcrypt).
    """
    # Always try new method first: pre-hash with SHA256, then verify with bcrypt
    # This handles passwords of any length
    pre_hashed = _pre_hash_password(plain_password)
    try:
        if pwd_context.verify(pre_hashed, hashed_password):
            return True
    except Exception:
        pass
    
    # Fallback to old method: direct bcrypt verification (for backward compatibility)
    # This handles existing passwords that were hashed without SHA256 pre-hashing
    # Only try this if password is <= 72 bytes (bcrypt limit)
    if len(plain_password.encode('utf-8')) <= 72:
        try:
            return pwd_context.verify(plain_password, hashed_password)
        except Exception:
            pass
    
    return False


def get_password_hash(password: str) -> str:
    """
    Hash password using SHA256 pre-hash + bcrypt.
    This allows passwords of any length while maintaining bcrypt security.
    
    IMPORTANT: Always pre-hash with SHA256 before bcrypt to avoid the 72-byte limit.
    """
    # Pre-hash with SHA256 to handle passwords longer than 72 bytes
    # SHA256 produces a 64-character hex string (32 bytes), well under bcrypt's 72-byte limit
    pre_hashed = _pre_hash_password(password)
    
    # Verify the pre-hashed password is within limits (should always be 64 chars = 32 bytes)
    pre_hashed_bytes = len(pre_hashed.encode('utf-8'))
    if pre_hashed_bytes > 72:
        # This should never happen, but just in case
        raise ValueError(f"Pre-hashed password is {pre_hashed_bytes} bytes, which exceeds bcrypt's 72-byte limit")
    
    # Then hash with bcrypt (the SHA256 hash is always 32 bytes, well under 72-byte limit)
    try:
        return pwd_context.hash(pre_hashed)
    except ValueError as e:
        error_msg = str(e)
        # If bcrypt complains about length (shouldn't happen), provide helpful error
        if "72 bytes" in error_msg or "longer than" in error_msg.lower():
            raise ValueError(
                f"Password hashing failed: {error_msg}. "
                f"This should not happen as passwords are pre-hashed. "
                f"Pre-hashed length: {pre_hashed_bytes} bytes. "
                f"Please restart the server to ensure code changes are loaded."
            ) from e
        raise


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def is_admin_user(user: User) -> bool:
    """Check if user is an admin. Admin users always have full access."""
    return user.role.value == "admin"


def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    """Authenticate user by email and password. All users are authorized."""
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    # All users are authorized - no is_active or is_verified checks
    # Admin users get special logging
    if is_admin_user(user):
        print(f"[AUTH] Admin user {user.email} authenticated - full access granted")
    return user


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # Decode and validate JWT token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id_str = payload.get("sub")
        if user_id_str is None:
            print(f"[AUTH] Token missing user ID in payload")
            raise credentials_exception
        # Convert string subject to integer user ID
        try:
            user_id: int = int(user_id_str)
        except (ValueError, TypeError) as e:
            print(f"[AUTH] Invalid user ID format in token: {user_id_str}")
            raise credentials_exception
    except ExpiredSignatureError:
        print(f"[AUTH] Token has expired")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except JWTError as e:
        print(f"[AUTH] JWT validation error: {e}")
        raise credentials_exception
    except Exception as e:
        print(f"[AUTH] Unexpected error validating token: {e}")
        raise credentials_exception
    
    # Get user from database
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if user is None:
            print(f"[AUTH] User {user_id} not found in database")
            raise credentials_exception
        # Admin users are always authorized - log for tracking
        if is_admin_user(user):
            print(f"[AUTH] Admin user {user.email} authenticated - full access granted")
        return user
    except Exception as e:
        print(f"[AUTH] Database error getting user: {e}")
        raise credentials_exception


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Get current active user. All users are authorized - no restrictions."""
    # All users are authorized - no checks for is_active or is_verified
    # Everyone can access the system
    return current_user


async def require_professor(
    current_user: User = Depends(get_current_active_user)
) -> User:
    if current_user.role.value not in ["professor", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user


async def require_admin(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """Require admin role. Only admin users can access endpoints using this dependency."""
    if not is_admin_user(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user

