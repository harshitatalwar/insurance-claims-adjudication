"""
Authentication service using PolicyHolder model (no separate User table)
"""
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
import hashlib
from sqlalchemy.orm import Session

from app.models.models import PolicyHolder
from app.schemas.auth import TokenData
from app.config import settings

# JWT settings
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash"""
    return get_password_hash(plain_password) == hashed_password

def get_password_hash(password: str) -> str:
    """Hash password using SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str) -> Optional[TokenData]:
    """Verify JWT token and return token data"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            return None
        return TokenData(email=email)
    except JWTError:
        return None

def authenticate_user(db: Session, email: str, password: str) -> Optional[PolicyHolder]:
    """Authenticate user with email and password using PolicyHolder"""
    policy_holder = db.query(PolicyHolder).filter(PolicyHolder.email == email).first()
    if not policy_holder:
        return None
    if not policy_holder.hashed_password:
        return None  # No password set
    if not verify_password(password, policy_holder.hashed_password):
        return None
    if not policy_holder.is_active:
        return None  # Account disabled
    return policy_holder

def get_user_by_email(db: Session, email: str) -> Optional[PolicyHolder]:
    """Get policy holder by email"""
    return db.query(PolicyHolder).filter(PolicyHolder.email == email).first()

def create_user(db: Session, email: str, password: str, full_name: str, role: str = "user") -> PolicyHolder:
    """Create new policy holder with auth credentials (not used - use policy_holders API instead)"""
    hashed_password = get_password_hash(password)
    policy_holder = PolicyHolder(
        email=email,
        hashed_password=hashed_password,
        policy_holder_name=full_name,
        is_active=True
    )
    db.add(policy_holder)
    db.commit()
    db.refresh(policy_holder)
    return policy_holder
