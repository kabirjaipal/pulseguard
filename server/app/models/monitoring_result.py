from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class MonitoringResult(Base):
    __tablename__ = "monitoring_results"

    id = Column(Integer, primary_key=True, index=True)
    endpoint_id = Column(Integer, ForeignKey("endpoints.id", ondelete="CASCADE"), nullable=False, index=True)
    status_code = Column(Integer, nullable=True) # Nullable in case request fails completely
    response_time_ms = Column(Integer, nullable=True) # Nullable in case of connection errors
    is_healthy = Column(Boolean, nullable=False, default=False)
    error_message = Column(String, nullable=True) # Nullable, details error if is_healthy is False
    checked_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    # Relationships
    endpoint = relationship("Endpoint", back_populates="results")
