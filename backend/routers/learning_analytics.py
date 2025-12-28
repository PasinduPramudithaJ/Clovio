from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from models import LearningAnalytics, ProjectMember, Project, User
from schemas import LearningAnalyticsCreate, LearningAnalyticsResponse
from auth import get_current_active_user

router = APIRouter(prefix="/api/learning-analytics", tags=["learning-analytics"])


@router.post("/", response_model=LearningAnalyticsResponse, status_code=status.HTTP_201_CREATED)
async def record_skill_development(
    analytics_data: LearningAnalyticsCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Record skill development for a user."""
    # If project_id is provided, verify access
    if analytics_data.project_id:
        project = db.query(Project).filter(Project.id == analytics_data.project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Check authorization
        if current_user.role.value not in ["professor", "admin"]:
            member = db.query(ProjectMember).filter(
                ProjectMember.project_id == analytics_data.project_id,
                ProjectMember.user_id == current_user.id
            ).first()
            if not member:
                raise HTTPException(status_code=403, detail="Not authorized")
    
    analytics = LearningAnalytics(
        user_id=current_user.id,
        project_id=analytics_data.project_id,
        skill_developed=analytics_data.skill_developed,
        proficiency_level=analytics_data.proficiency_level,
        evidence=analytics_data.evidence
    )
    
    db.add(analytics)
    db.commit()
    db.refresh(analytics)
    
    return analytics


@router.get("/", response_model=List[LearningAnalyticsResponse])
async def get_learning_analytics(
    user_id: int = None,
    project_id: int = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get learning analytics with optional filters."""
    target_user_id = user_id if user_id else current_user.id
    
    # Check authorization
    if target_user_id != current_user.id and current_user.role.value not in ["professor", "admin"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    query = db.query(LearningAnalytics).filter(LearningAnalytics.user_id == target_user_id)
    
    if project_id:
        query = query.filter(LearningAnalytics.project_id == project_id)
        # Check project access
        if current_user.role.value not in ["professor", "admin"]:
            member = db.query(ProjectMember).filter(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == current_user.id
            ).first()
            if not member:
                raise HTTPException(status_code=403, detail="Not authorized")
    
    analytics = query.order_by(LearningAnalytics.recorded_at.desc()).all()
    return analytics


@router.get("/{analytics_id}", response_model=LearningAnalyticsResponse)
async def get_learning_analytics_entry(
    analytics_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get a specific learning analytics entry."""
    analytics = db.query(LearningAnalytics).filter(LearningAnalytics.id == analytics_id).first()
    if not analytics:
        raise HTTPException(status_code=404, detail="Learning analytics entry not found")
    
    # Check authorization
    if analytics.user_id != current_user.id and current_user.role.value not in ["professor", "admin"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    return analytics


@router.delete("/{analytics_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_learning_analytics(
    analytics_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete a learning analytics entry."""
    analytics = db.query(LearningAnalytics).filter(LearningAnalytics.id == analytics_id).first()
    if not analytics:
        raise HTTPException(status_code=404, detail="Learning analytics entry not found")
    
    # Only owner or professor can delete
    if analytics.user_id != current_user.id and current_user.role.value not in ["professor", "admin"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    db.delete(analytics)
    db.commit()
    return None

