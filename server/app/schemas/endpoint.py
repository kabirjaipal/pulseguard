from pydantic import BaseModel, HttpUrl
from datetime import datetime

class EndpointBase(BaseModel):
    name: str
    url: str # String validation for flexibility (or HttpUrl if strict)
    method: str = "GET"
    check_interval: int = 60 # Default to 60 seconds
    is_active: bool = True

class EndpointCreate(EndpointBase):
    project_id: int

class EndpointUpdate(BaseModel):
    name: str | None = None
    url: str | None = None
    method: str | None = None
    check_interval: int | None = None
    is_active: bool | None = None

class EndpointOut(EndpointBase):
    id: int
    project_id: int
    created_at: datetime
    last_checked_at: datetime | None = None
    status: str
    consecutive_failures: int

    model_config = {
        "from_attributes": True
    }
