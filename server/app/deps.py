from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
import jwt
from jwt.exceptions import InvalidTokenError

from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.schemas.user import TokenData

# OAuth2PasswordBearer configures FastAPI to look for the Bearer token in the Authorization header.
# 'tokenUrl' is the path where the client logs in to get the token.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    """
    Dependency that extracts the current logged-in user from the JWT token in the request header.
    If token is invalid or user doesn't exist, raises 401 Unauthorized.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # 1. Decode the JWT token using our SECRET_KEY and ALGORITHM
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub") # 'sub' is standard for subject (user email/id)
        if email is None:
            raise credentials_exception
        token_data = TokenData(email=email)
    except InvalidTokenError:
        raise credentials_exception
        
    # 2. Retrieve user from the database
    user = db.query(User).filter(User.email == token_data.email).first()
    if user is None:
        raise credentials_exception
        
    # 3. Return the authenticated user object
    return user
