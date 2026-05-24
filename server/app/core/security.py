from datetime import datetime, timedelta, timezone
import jwt
import bcrypt
from app.core.config import settings

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Compare a plain-text password with a hashed password to see if they match."""
    pwd_bytes = plain_password.encode('utf-8')
    hashed_bytes = hashed_password.encode('utf-8')
    return bcrypt.checkpw(pwd_bytes, hashed_bytes)

def get_password_hash(password: str) -> str:
    """Hash a password securely using bcrypt."""
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(pwd_bytes, salt)
    return hashed.decode('utf-8')

# 2. Setup JWT Access Token Utilities
def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Generate a JWT token containing data (like user ID) and an expiration time."""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        
    # 'exp' is a standard JWT claim representing the expiration time
    to_encode.update({"exp": expire})
    
    # Sign and encode the token using our SECRET_KEY and ALGORITHM
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt
