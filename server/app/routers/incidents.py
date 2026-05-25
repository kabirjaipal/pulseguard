from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import json

from app.core.database import get_db
from app.deps import get_current_user
from app.models.user import User
from app.models.project import Project
from app.models.endpoint import Endpoint
from app.models.monitoring_result import MonitoringResult
from app.models.incident_analysis import IncidentAnalysis
from app.schemas.incident_analysis import IncidentAnalysisOut
from app.core.ai import generate_incident_analysis
from app.core.limiter import RateLimiter

# Initialize router with 60 requests per minute rate limit per user
router = APIRouter(
    prefix="/api/incidents",
    tags=["Incidents"],
    dependencies=[Depends(RateLimiter(requests_limit=60, window_seconds=60, scope="incidents"))]
)

@router.get("/endpoint/{endpoint_id}", response_model=List[IncidentAnalysisOut])
def get_endpoint_analyses(
    endpoint_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieve all AI incident reports for a monitored endpoint."""
    # 1. Verify ownership of the endpoint's project
    endpoint = db.query(Endpoint).join(Project).filter(
        Endpoint.id == endpoint_id,
        Project.owner_id == current_user.id
    ).first()
    
    if not endpoint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Endpoint not found or not owned by you."
        )
        
    return endpoint.analyses

@router.post("/endpoint/{endpoint_id}/analyze", response_model=IncidentAnalysisOut, status_code=status.HTTP_201_CREATED)
def analyze_endpoint_manually(
    endpoint_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Manually triggers a new AI analysis for the endpoint using its recent failed logs,
    saves the analysis report in the database, and returns it.
    """
    # 1. Verify ownership of the endpoint's project
    endpoint = db.query(Endpoint).join(Project).filter(
        Endpoint.id == endpoint_id,
        Project.owner_id == current_user.id
    ).first()
    
    if not endpoint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Endpoint not found or not owned by you."
        )
        
    # 2. Fetch the latest 5 failed results
    failed_results = db.query(MonitoringResult).filter(
        MonitoringResult.endpoint_id == endpoint_id,
        MonitoringResult.is_healthy == False
    ).order_by(MonitoringResult.checked_at.desc()).limit(5).all()
    
    if not failed_results:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No failed check logs found for this endpoint. Only failed endpoints can be analyzed."
        )
        
    # 3. Generate AI analysis
    ai_analysis = generate_incident_analysis(endpoint, failed_results)
    
    # 4. Save to database
    analysis_log = IncidentAnalysis(
        endpoint_id=endpoint.id,
        summary=ai_analysis.get("summary", "No summary generated"),
        suggestions=ai_analysis.get("suggestions", "No suggestions generated"),
        raw_logs=json.dumps([
            {
                "status_code": r.status_code,
                "latency_ms": r.response_time_ms,
                "is_healthy": r.is_healthy,
                "error_message": r.error_message,
                "checked_at": r.checked_at.isoformat() if r.checked_at else None
            } for r in failed_results
        ])
    )
    db.add(analysis_log)
    db.commit()
    db.refresh(analysis_log)
    
    return analysis_log
