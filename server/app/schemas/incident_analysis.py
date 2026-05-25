from pydantic import BaseModel
from datetime import datetime

class IncidentAnalysisOut(BaseModel):
    id: int
    endpoint_id: int
    summary: str
    suggestions: str
    raw_logs: str | None = None
    created_at: datetime

    model_config = {
        "from_attributes": True
    }
