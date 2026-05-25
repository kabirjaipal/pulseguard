from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_password_hash, verify_password, create_access_token
from app.models.user import User
from app.schemas.user import UserCreate, UserOut, Token
from app.core.limiter import RateLimiter

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

@router.post("/signup", response_model=UserOut, status_code=status.HTTP_201_CREATED, dependencies=[Depends(RateLimiter(requests_limit=10, window_seconds=60, scope="auth_signup"))])
def signup(user_in: UserCreate, db: Session = Depends(get_db)):
    """Register a new user in the platform."""
    # 1. Check if user already exists
    existing_user = db.query(User).filter(User.email == user_in.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered."
        )
        
    # 2. Hash the password and save to DB
    hashed_pw = get_password_hash(user_in.password)
    new_user = User(email=user_in.email, hashed_password=hashed_pw)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return new_user

@router.post("/login", response_model=Token, dependencies=[Depends(RateLimiter(requests_limit=10, window_seconds=60, scope="auth_login"))])
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """
    Authenticate user and return a JWT access token.
    FastAPI OAuth2 standard expects standard form-data (username and password).
    In our app, we use email as the username.
    """
    # 1. Fetch user by email (username)
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect email or password."
        )
        
    # 2. Generate and return the JWT token
    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}
