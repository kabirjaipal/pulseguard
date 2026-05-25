from sqlalchemy import Column, Integer, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class IncidentAnalysis(Base):
    __tablename__ = "incident_analyses"

    id = Column(Integer, primary_key=True, index=True)
    endpoint_id = Column(Integer, ForeignKey("endpoints.id", ondelete="CASCADE"), nullable=False, index=True)
    summary = Column(Text, nullable=False) # AI Root Cause Summary
    suggestions = Column(Text, nullable=False) # AI Troubleshooting Recommendations
    raw_logs = Column(Text, nullable=True) # Serialized JSON representing logs analyzed
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    # Relationships
    endpoint = relationship("Endpoint", back_populates="analyses")
