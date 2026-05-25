# Import all models here so that they are registered on the Base metadata
# before database tables are created.
from app.core.database import Base
from app.models.user import User
from app.models.project import Project
from app.models.endpoint import Endpoint
from app.models.monitoring_result import MonitoringResult
from app.models.incident_analysis import IncidentAnalysis

__all__ = ["Base", "User", "Project", "Endpoint", "MonitoringResult", "IncidentAnalysis"]
