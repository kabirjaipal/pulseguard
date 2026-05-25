from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class Endpoint(Base):
    __tablename__ = "endpoints"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    url = Column(String, nullable=False)
    method = Column(String, default="GET", nullable=False) # e.g., GET, POST
    check_interval = Column(Integer, default=60, nullable=False) # check every X seconds
    is_active = Column(Boolean, default=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_checked_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String, default="healthy", nullable=False)
    consecutive_failures = Column(Integer, default=0, nullable=False)

    # Relationships
    project = relationship("Project", back_populates="endpoints")
    results = relationship("MonitoringResult", back_populates="endpoint", cascade="all, delete-orphan")
