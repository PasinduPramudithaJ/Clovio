from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Dict
from database import get_db
from models import (
    Project, Task, Contribution, ProjectMember, User, LearningAnalytics
)
from schemas import ProjectAnalytics, UserAnalytics
from auth import get_current_active_user, require_professor

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/project/{project_id}", response_model=ProjectAnalytics)
async def get_project_analytics(
    project_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Get analytics for a specific project."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Check authorization
    if current_user.role.value not in ["professor", "admin"]:
        member = db.query(ProjectMember).filter(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == current_user.id
        ).first()
        if not member:
            raise HTTPException(status_code=403, detail="Not authorized")
    
    # Get task statistics
    total_tasks = db.query(Task).filter(Task.project_id == project_id).count()
    completed_tasks = db.query(Task).filter(
        Task.project_id == project_id,
        Task.status == "completed"
    ).count()
    in_progress_tasks = db.query(Task).filter(
        Task.project_id == project_id,
        Task.status == "in_progress"
    ).count()
    
    # Get total hours
    total_hours_result = db.query(func.sum(Task.actual_hours)).filter(
        Task.project_id == project_id
    ).scalar()
    total_hours = float(total_hours_result) if total_hours_result else 0.0
    
    # Get member contributions
    members = db.query(ProjectMember).filter(ProjectMember.project_id == project_id).all()
    member_contributions = []
    
    for member in members:
        user = db.query(User).filter(User.id == member.user_id).first()
        user_tasks = db.query(Task).filter(
            Task.project_id == project_id,
            Task.assigned_to_id == member.user_id
        ).all()
        
        user_hours = sum(task.actual_hours for task in user_tasks)
        user_completed = sum(1 for task in user_tasks if task.status == "completed")
        
        member_contributions.append({
            "user_id": member.user_id,
            "user_name": user.full_name if user else "Unknown",
            "tasks_assigned": len(user_tasks),
            "tasks_completed": user_completed,
            "hours_spent": user_hours
        })
    
    # Get skill distribution
    all_tasks = db.query(Task).filter(Task.project_id == project_id).all()
    skill_distribution = {}
    for task in all_tasks:
        if task.required_skills:
            for skill in task.required_skills:
                skill_distribution[skill] = skill_distribution.get(skill, 0) + 1
    
    return {
        "project_id": project_id,
        "total_tasks": total_tasks,
        "completed_tasks": completed_tasks,
        "in_progress_tasks": in_progress_tasks,
        "total_hours": total_hours,
        "member_contributions": member_contributions,
        "skill_distribution": skill_distribution
    }


@router.get("/user/{user_id}", response_model=UserAnalytics)
async def get_user_analytics(
    user_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Get analytics for a specific user."""
    # Check authorization
    if current_user.id != user_id and current_user.role.value not in ["professor", "admin"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get project count
    member_projects = db.query(ProjectMember).filter(ProjectMember.user_id == user_id).all()
    total_projects = len(member_projects)
    
    # Get task statistics
    user_tasks = db.query(Task).filter(Task.assigned_to_id == user_id).all()
    completed_tasks = sum(1 for task in user_tasks if task.status == "completed")
    total_hours = sum(task.actual_hours for task in user_tasks)
    
    # Get skills developed
    analytics = db.query(LearningAnalytics).filter(LearningAnalytics.user_id == user_id).all()
    skills_developed = list(set([a.skill_developed for a in analytics]))
    
    # Get contribution breakdown
    contributions = db.query(Contribution).filter(Contribution.user_id == user_id).all()
    contribution_breakdown = {}
    for contrib in contributions:
        contrib_type = contrib.contribution_type
        contribution_breakdown[contrib_type] = contribution_breakdown.get(contrib_type, 0) + 1
    
    return {
        "user_id": user_id,
        "total_projects": total_projects,
        "completed_tasks": completed_tasks,
        "total_hours": total_hours,
        "skills_developed": skills_developed,
        "contribution_breakdown": contribution_breakdown
    }


@router.get("/dashboard", response_model=Dict)
async def get_dashboard_analytics(
    db: Session = Depends(get_db),
    current_user = Depends(require_professor)
):
    """Get dashboard analytics for professors."""
    # Total projects
    total_projects = db.query(Project).count()
    active_projects = db.query(Project).filter(Project.status == "active").count()
    
    # Total users
    total_students = db.query(User).filter(User.role == "student").count()
    total_professors = db.query(User).filter(User.role == "professor").count()
    
    # Task statistics
    total_tasks = db.query(Task).count()
    completed_tasks = db.query(Task).filter(Task.status == "completed").count()
    
    # Recent activity
    recent_projects = db.query(Project).order_by(Project.created_at.desc()).limit(5).all()
    
    return {
        "total_projects": total_projects,
        "active_projects": active_projects,
        "total_students": total_students,
        "total_professors": total_professors,
        "total_tasks": total_tasks,
        "completed_tasks": completed_tasks,
        "completion_rate": (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0,
        "recent_projects": [
            {
                "id": p.id,
                "title": p.title,
                "created_at": p.created_at.isoformat() if p.created_at else None
            }
            for p in recent_projects
        ]
    }

