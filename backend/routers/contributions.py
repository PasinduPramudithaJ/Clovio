from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from models import Contribution, ProjectMember, Project, User
from schemas import ContributionCreate, ContributionResponse
from auth import get_current_active_user

router = APIRouter(prefix="/api/contributions", tags=["contributions"])


@router.post("/", response_model=ContributionResponse, status_code=status.HTTP_201_CREATED)
async def create_contribution(
    contribution_data: ContributionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Record a contribution to a project."""
    # Verify project exists and user has access
    project = db.query(Project).filter(Project.id == contribution_data.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Check authorization - user must be a project member
    if current_user.role.value not in ["professor", "admin"]:
        member = db.query(ProjectMember).filter(
            ProjectMember.project_id == contribution_data.project_id,
            ProjectMember.user_id == current_user.id
        ).first()
        if not member:
            raise HTTPException(status_code=403, detail="Not authorized")
    
    # Users can only record their own contributions
    if contribution_data.user_id and contribution_data.user_id != current_user.id:
        if current_user.role.value not in ["professor", "admin"]:
            raise HTTPException(status_code=403, detail="Can only record your own contributions")
    
    contribution = Contribution(
        project_id=contribution_data.project_id,
        user_id=current_user.id,
        task_id=contribution_data.task_id,
        contribution_type=contribution_data.contribution_type,
        description=contribution_data.description,
        hours_spent=contribution_data.hours_spent
    )
    
    db.add(contribution)
    db.commit()
    db.refresh(contribution)
    
    # Get user name for response
    user = db.query(User).filter(User.id == current_user.id).first()
    
    return {
        "id": contribution.id,
        "project_id": contribution.project_id,
        "user_id": contribution.user_id,
        "user_name": user.full_name if user else "Unknown",
        "task_id": contribution.task_id,
        "contribution_type": contribution.contribution_type,
        "description": contribution.description,
        "hours_spent": contribution.hours_spent,
        "created_at": contribution.created_at
    }


@router.get("/", response_model=List[ContributionResponse])
async def get_contributions(
    project_id: int = None,
    user_id: int = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get contributions with optional filters."""
    query = db.query(Contribution)
    
    if project_id:
        query = query.filter(Contribution.project_id == project_id)
        # Check authorization
        if current_user.role.value not in ["professor", "admin"]:
            member = db.query(ProjectMember).filter(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == current_user.id
            ).first()
            if not member:
                raise HTTPException(status_code=403, detail="Not authorized")
    
    if user_id:
        query = query.filter(Contribution.user_id == user_id)
        # Users can only see their own contributions unless professor
        if current_user.id != user_id and current_user.role.value not in ["professor", "admin"]:
            raise HTTPException(status_code=403, detail="Not authorized")
    
    contributions = query.order_by(Contribution.created_at.desc()).all()
    
    # Get user names
    result = []
    for contrib in contributions:
        user = db.query(User).filter(User.id == contrib.user_id).first()
        result.append({
            "id": contrib.id,
            "project_id": contrib.project_id,
            "user_id": contrib.user_id,
            "user_name": user.full_name if user else "Unknown",
            "task_id": contrib.task_id,
            "contribution_type": contrib.contribution_type,
            "description": contrib.description,
            "hours_spent": contrib.hours_spent,
            "created_at": contrib.created_at
        })
    
    return result


@router.get("/{contribution_id}", response_model=ContributionResponse)
async def get_contribution(
    contribution_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get a specific contribution."""
    contribution = db.query(Contribution).filter(Contribution.id == contribution_id).first()
    if not contribution:
        raise HTTPException(status_code=404, detail="Contribution not found")
    
    # Check authorization
    if current_user.id != contribution.user_id and current_user.role.value not in ["professor", "admin"]:
        member = db.query(ProjectMember).filter(
            ProjectMember.project_id == contribution.project_id,
            ProjectMember.user_id == current_user.id
        ).first()
        if not member:
            raise HTTPException(status_code=403, detail="Not authorized")
    
    user = db.query(User).filter(User.id == contribution.user_id).first()
    return {
        "id": contribution.id,
        "project_id": contribution.project_id,
        "user_id": contribution.user_id,
        "user_name": user.full_name if user else "Unknown",
        "task_id": contribution.task_id,
        "contribution_type": contribution.contribution_type,
        "description": contribution.description,
        "hours_spent": contribution.hours_spent,
        "created_at": contribution.created_at
    }


@router.delete("/{contribution_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_contribution(
    contribution_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete a contribution."""
    contribution = db.query(Contribution).filter(Contribution.id == contribution_id).first()
    if not contribution:
        raise HTTPException(status_code=404, detail="Contribution not found")
    
    # Only owner or professor can delete
    if contribution.user_id != current_user.id and current_user.role.value not in ["professor", "admin"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    db.delete(contribution)
    db.commit()
    return None

