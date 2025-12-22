"""
Authentication API endpoints using PolicyHolder model
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta

from app.utils.database import get_db
from app.schemas.schemas import PolicyHolderResponse
from app.services.auth_service import (
    authenticate_user,
    create_access_token,
    get_user_by_email,
    verify_token,
    ACCESS_TOKEN_EXPIRE_MINUTES
)
from app.models.models import PolicyHolder
from pydantic import BaseModel, EmailStr

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

# Request schemas
class RegisterRequest(BaseModel):
    full_name: str
    email: EmailStr
    phone: str
    date_of_birth: str
    password: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> PolicyHolder:
    """Get current authenticated policy holder from token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    token_data = verify_token(token)
    if token_data is None or token_data.email is None:
        raise credentials_exception
    
    user = get_user_by_email(db, email=token_data.email)
    if user is None:
        raise credentials_exception
    
    return user

async def get_current_active_user(
    current_user: PolicyHolder = Depends(get_current_user)
) -> PolicyHolder:
    """Get current active policy holder"""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

@router.post("/register", response_model=TokenResponse)
async def register(user_data: RegisterRequest, db: Session = Depends(get_db)):
    """Register new policy holder"""
    # Check if email already exists
    existing_user = get_user_by_email(db, email=user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Import here to avoid circular dependency
    from app.models import PolicyHolder
    from app.services.auth_service import get_password_hash
    from datetime import datetime, timedelta
    from app.utils.id_generator import generate_policy_holder_id
    
    # Generate policy holder ID using atomic PostgreSQL sequence
    # This is O(1), thread-safe, and prevents race conditions
    generated_id = generate_policy_holder_id(db)
    
    # Set registration datetime (current time)
    registration_datetime = datetime.utcnow()
    
    # Policy terms ID from policy_terms.json
    policy_terms_id = "PLUM_OPD_2024"
    
    # Calculate waiting period completion
    # Initial waiting period is 30 days (from policy_terms.json)
    # For new registrations, waiting period is NOT completed yet
    # It will be completed after 30 days from join_date
    initial_waiting_days = 30
    waiting_period_end_date = registration_datetime + timedelta(days=initial_waiting_days)
    waiting_period_completed = False  # Always False for new registrations
    
    # Create policy holder directly with all required fields
    policy_holder = PolicyHolder(
        policy_holder_id=generated_id,
        policy_holder_name=user_data.full_name,
        email=user_data.email,
        phone=user_data.phone,
        dob=user_data.date_of_birth,
        join_date=registration_datetime,              # Current datetime
        policy_terms_id=policy_terms_id,              # PLUM_OPD_2024
        policy_start_date=registration_datetime,      # Same as join_date initially
        policy_status="ACTIVE",                       # Set to ACTIVE
        waiting_period_completed=waiting_period_completed,  # False for new users
        annual_limit=50000.0,                         # From policy_terms.json
        annual_limit_used=0.0,                        # No usage yet
        pre_existing_conditions=[],                   # Empty for new users
        hashed_password=get_password_hash(user_data.password),
        is_active=True,
        created_at=registration_datetime,
        updated_at=registration_datetime
    )
    
    db.add(policy_holder)
    db.commit()
    db.refresh(policy_holder)
    
    logger.info(f"✅ Created policy holder: {policy_holder.policy_holder_id} for {policy_holder.email}")
    logger.info(f"   Policy Terms: {policy_terms_id}")
    logger.info(f"   Join Date: {registration_datetime.isoformat()}")
    logger.info(f"   Waiting Period Ends: {waiting_period_end_date.isoformat()}")
    
    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": policy_holder.email}, expires_delta=access_token_expires
    )
    
    return TokenResponse(access_token=access_token)

@router.post("/login", response_model=TokenResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """Login with email and password"""
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    
    return TokenResponse(access_token=access_token)

@router.post("/login/json", response_model=TokenResponse)
async def login_json(user_data: LoginRequest, db: Session = Depends(get_db)):
    """Login with JSON body (for frontend)"""
    user = authenticate_user(db, user_data.email, user_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    
    return TokenResponse(access_token=access_token)

@router.get("/me", response_model=PolicyHolderResponse)
async def get_me(current_user: PolicyHolder = Depends(get_current_active_user)):
    """Get current policy holder info"""
    return PolicyHolderResponse.from_orm(current_user)

@router.post("/logout")
async def logout(current_user: PolicyHolder = Depends(get_current_active_user)):
    """Logout (client should delete token)"""
    return {"message": "Successfully logged out"}
