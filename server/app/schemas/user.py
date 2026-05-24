from pydantic import BaseModel, EmailStr
from datetime import datetime

# Note: Pydantic v2 is used by FastAPI now.
# We define 'from_attributes = True' in model_config so Pydantic can read ORM/SQLAlchemy objects.

class UserBase(BaseModel):
    email: EmailStr

class UserCreate(UserBase):
    password: str

class UserOut(UserBase):
    id: int
    is_active: bool
    created_at: datetime

    model_config = {
        "from_attributes": True
    }

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: str | None = None
