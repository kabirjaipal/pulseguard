from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.deps import get_current_user
from app.models.user import User
from app.models.project import Project
from app.models.endpoint import Endpoint
from app.schemas.endpoint import EndpointCreate, EndpointOut

router = APIRouter(prefix="/api/endpoints", tags=["Endpoints"])

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
