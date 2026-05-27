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
from app.schemas.endpoint import EndpointCreate, EndpointOut
from app.schemas.monitoring_result import MonitoringResultOut
from app.core.redis_client import redis_client
from app.core.limiter import RateLimiter

# Initialize router and protect all routes with a rate limit of 60 requests per minute per user
router = APIRouter(
    prefix="/api/endpoints",
    tags=["Endpoints"],
    dependencies=[Depends(RateLimiter(requests_limit=60, window_seconds=60, scope="endpoints"))]
)

@router.post("/", response_model=EndpointOut, status_code=status.HTTP_201_CREATED)
def create_endpoint(
    endpoint_in: EndpointCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Add a new API endpoint to monitor under a specific project."""
    # 1. Verify project exists and belongs to current user
    project = db.query(Project).filter(Project.id == endpoint_in.project_id, Project.owner_id == current_user.id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found or not owned by you."
        )
        
    # 2. Create and save the endpoint
    new_endpoint = Endpoint(
        name=endpoint_in.name,
        url=endpoint_in.url,
        method=endpoint_in.method,
        check_interval=endpoint_in.check_interval,
        is_active=endpoint_in.is_active,
        project_id=endpoint_in.project_id
    )
    db.add(new_endpoint)
    db.commit()
    db.refresh(new_endpoint)
    return new_endpoint

@router.get("/", response_model=List[EndpointOut])
def get_endpoints(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieve all endpoints that belong to all projects owned by the user."""
    # We join Endpoint with Project to filter by the project owner
    endpoints = db.query(Endpoint).join(Project).filter(Project.owner_id == current_user.id).all()
    return endpoints

@router.get("/project/{project_id}", response_model=List[EndpointOut])
def get_endpoints_by_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieve all endpoints belonging to a specific project owned by the user."""
    # 1. Verify project ownership
    project = db.query(Project).filter(Project.id == project_id, Project.owner_id == current_user.id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found or not owned by you."
        )
    return project.endpoints

@router.delete("/{endpoint_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_endpoint(
    endpoint_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a monitored API endpoint."""
    # We find the endpoint and check that its parent project is owned by the current user
    endpoint = db.query(Endpoint).join(Project).filter(
        Endpoint.id == endpoint_id,
        Project.owner_id == current_user.id
    ).first()
    
    if not endpoint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Endpoint not found or not owned by you."
        )
        
    db.delete(endpoint)
    db.commit()
    return

@router.get("/{endpoint_id}/history", response_model=List[MonitoringResultOut])
def get_endpoint_history(
    endpoint_id: int,
    limit: int = 30,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieve recent check history logs for a monitored endpoint."""
    # 1. Verify ownership of the endpoint
    endpoint = db.query(Endpoint).join(Project).filter(
        Endpoint.id == endpoint_id,
        Project.owner_id == current_user.id
    ).first()
    
    if not endpoint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Endpoint not found or not owned by you."
        )
        
    # 2. Fetch history records
    results = db.query(MonitoringResult).filter(
        MonitoringResult.endpoint_id == endpoint_id
    ).order_by(MonitoringResult.checked_at.desc()).limit(limit).all()
    
    # Reverse so they are chronologically ascending (left-to-right on charts)
    results.reverse()
    return results

@router.get("/{endpoint_id}", response_model=EndpointOut)
def get_endpoint(
    endpoint_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieve details for a specific monitored endpoint."""
    endpoint = db.query(Endpoint).join(Project).filter(
        Endpoint.id == endpoint_id,
        Project.owner_id == current_user.id
    ).first()
    
    if not endpoint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Endpoint not found or not owned by you."
        )
    return endpoint

@router.get("/{endpoint_id}/latest", response_model=MonitoringResultOut)
def get_latest_endpoint_result(
    endpoint_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieve the latest check result for a given endpoint.
    Attempts to fetch from Redis cache first; falls back to database query if empty.
    """
    # 1. Verify endpoint ownership
    endpoint = db.query(Endpoint).join(Project).filter(
        Endpoint.id == endpoint_id,
        Project.owner_id == current_user.id
    ).first()
    
    if not endpoint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Endpoint not found or not owned by you."
        )
        
    # 2. Try fetching from Redis Cache
    cache_key = f"endpoint:{endpoint_id}:latest"
    try:
        cached_data = redis_client.get(cache_key)
        if cached_data:
            return json.loads(cached_data)
    except Exception as e:
        print(f"Error reading from Redis cache: {str(e)}")
        
    # 3. Cache Miss: Query the PostgreSQL database for the latest check
    latest_result = db.query(MonitoringResult).filter(
        MonitoringResult.endpoint_id == endpoint_id
    ).order_by(MonitoringResult.checked_at.desc()).first()
    
    if not latest_result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No monitoring results found for this endpoint yet."
        )
        
    # 4. Write back to Redis cache
    try:
        cache_payload = {
            "id": latest_result.id,
            "endpoint_id": latest_result.endpoint_id,
            "status_code": latest_result.status_code,
            "response_time_ms": latest_result.response_time_ms,
            "is_healthy": latest_result.is_healthy,
            "error_message": latest_result.error_message,
            "checked_at": latest_result.checked_at.isoformat()
        }
        expire_seconds = max(endpoint.check_interval * 2, 120)
        redis_client.setex(cache_key, expire_seconds, json.dumps(cache_payload))
    except Exception as e:
        print(f"Error writing to Redis cache: {str(e)}")
        
    return latest_result

@router.post("/{endpoint_id}/ping", status_code=status.HTTP_202_ACCEPTED)
def trigger_ping_manually(
    endpoint_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Manually dispatch a check ping for an endpoint into the Celery task queue."""
    # 1. Verify endpoint ownership
    endpoint = db.query(Endpoint).join(Project).filter(
        Endpoint.id == endpoint_id,
        Project.owner_id == current_user.id
    ).first()
    
    if not endpoint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Endpoint not found or not owned by you."
        )
        
    # 2. Dispatch Celery ping task immediately
    from app.core.tasks import ping_endpoint_task
    ping_endpoint_task.delay(endpoint.id)
    return {"message": "Check triggered and queued."}

