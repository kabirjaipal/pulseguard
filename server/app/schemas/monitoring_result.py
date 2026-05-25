from pydantic import BaseModel
from datetime import datetime

class MonitoringResultOut(BaseModel):
    id: int
    endpoint_id: int
    status_code: int | None = None
    response_time_ms: int | None = None
    is_healthy: bool
    error_message: str | None = None
    checked_at: datetime

    model_config = {
        "from_attributes": True
    }
