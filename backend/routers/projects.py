from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from models import Project, ProjectMember, Task, Document, ChatMessage, User
from schemas import (
    ProjectCreate, ProjectResponse, ProjectDetail, TaskResponse
)
from auth import get_current_active_user, require_professor
from ai.task_breakdown import break_down_project
from datetime import datetime

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.post("/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_data: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new project."""
    project = Project(
        title=project_data.title,
        description=project_data.description,
        course_code=project_data.course_code,
        course_name=project_data.course_name,
        deadline=project_data.deadline,
        created_by_id=current_user.id
    )
    
    db.add(project)
    db.commit()
    db.refresh(project)
    
    # Add creator as member
    creator_member = ProjectMember(
        project_id=project.id,
        user_id=current_user.id,
        role="leader"
    )
    db.add(creator_member)
    
    # Add other members if specified
    for member_id in project_data.member_ids:
        if member_id != current_user.id:
            member = ProjectMember(project_id=project.id, user_id=member_id)
            db.add(member)
    
    db.commit()
    
    return project


@router.get("/", response_model=List[ProjectResponse])
async def get_projects(
    skip: int = 0,
    limit: int = 100,
    enrolled_only: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get projects. Professors see all, others see all projects but can filter by enrollment."""
    if current_user.role.value in ["professor", "admin"]:
        # Professors can see all projects
        projects = db.query(Project).offset(skip).limit(limit).all()
    else:
        if enrolled_only:
            # Show only enrolled projects
            member_projects = db.query(ProjectMember).filter(
                ProjectMember.user_id == current_user.id
            ).all()
            project_ids = [mp.project_id for mp in member_projects]
            if project_ids:
                projects = db.query(Project).filter(Project.id.in_(project_ids)).offset(skip).limit(limit).all()
            else:
                projects = []
        else:
            # Show all projects (users can see all but need to enroll to access)
            projects = db.query(Project).offset(skip).limit(limit).all()
    
    return projects


@router.get("/{project_id}", response_model=ProjectDetail)
async def get_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get project details. Any user can view project details, but tasks are filtered by enrollment."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Check if user is enrolled (for task filtering)
    is_enrolled = False
    if current_user.role.value not in ["professor", "admin"]:
        member = db.query(ProjectMember).filter(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == current_user.id
        ).first()
        is_enrolled = member is not None
    else:
        is_enrolled = True  # Professors can see all tasks
    
    # Get members
    members = db.query(ProjectMember).filter(ProjectMember.project_id == project_id).all()
    member_users = [db.query(User).filter(User.id == m.user_id).first() for m in members]
    
    # Get tasks - only show if user is enrolled (or is professor)
    if is_enrolled:
        tasks = db.query(Task).filter(Task.project_id == project_id).all()
    else:
        tasks = []  # Empty list if not enrolled
    
    # Get document count
    doc_count = db.query(Document).filter(Document.project_id == project_id).count()
    
    # Get message count
    msg_count = db.query(ChatMessage).filter(ChatMessage.project_id == project_id).count()
    
    return {
        **project.__dict__,
        "members": member_users,
        "tasks": tasks,
        "document_count": doc_count,
        "message_count": msg_count
    }


@router.post("/{project_id}/breakdown", response_model=List[TaskResponse])
async def breakdown_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Use AI to break down project into tasks."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Check authorization
    if current_user.role.value not in ["professor", "admin"]:
        member = db.query(ProjectMember).filter(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == current_user.id
        ).first()
        if not member or member.role != "leader":
            raise HTTPException(status_code=403, detail="Only project leaders can break down projects")
    
    # Use AI to break down project
    deadline_str = project.deadline.isoformat() if isinstance(project.deadline, datetime) else str(project.deadline)
    task_data_list = await break_down_project(project.description, deadline_str)
    
    created_tasks = []
    for task_data in task_data_list:
        task = Task(
            project_id=project_id,
            title=task_data.get("title", "Untitled Task"),
            description=task_data.get("description", ""),
            priority=task_data.get("priority", "medium"),
            required_skills=task_data.get("required_skills", []),
            estimated_hours=task_data.get("estimated_hours")
        )
        db.add(task)
        created_tasks.append(task)
    
    project.ai_assigned = True
    db.commit()
    
    for task in created_tasks:
        db.refresh(task)
    
    return created_tasks


@router.post("/{project_id}/members/{user_id}", status_code=status.HTTP_201_CREATED)
async def add_project_member(
    project_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Add a member to a project. Any user can enroll themselves or professors can add others."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Check authorization - users can only add themselves unless they're professors
    if current_user.role.value not in ["professor", "admin"]:
        if user_id != current_user.id:
            raise HTTPException(status_code=403, detail="You can only enroll yourself")
    
    # Check if user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if already a member
    existing = db.query(ProjectMember).filter(
        ProjectMember.project_id == project_id,
        ProjectMember.user_id == user_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="User is already a member")
    
    member = ProjectMember(project_id=project_id, user_id=user_id)
    db.add(member)
    db.commit()
    
    return {"message": "Member added successfully"}


@router.post("/{project_id}/enroll", status_code=status.HTTP_201_CREATED)
async def enroll_in_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Enroll current user in a project. Any user can enroll in any project."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Check if already a member
    existing = db.query(ProjectMember).filter(
        ProjectMember.project_id == project_id,
        ProjectMember.user_id == current_user.id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="You are already enrolled in this project")
    
    member = ProjectMember(project_id=project_id, user_id=current_user.id)
    db.add(member)
    db.commit()
    
    return {"message": "Successfully enrolled in project"}


@router.delete("/{project_id}/enroll", status_code=status.HTTP_204_NO_CONTENT)
async def unenroll_from_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Unenroll current user from a project. Any user can unenroll themselves."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Find membership
    member = db.query(ProjectMember).filter(
        ProjectMember.project_id == project_id,
        ProjectMember.user_id == current_user.id
    ).first()
    
    if not member:
        raise HTTPException(status_code=404, detail="You are not enrolled in this project")
    
    # Prevent unenrolling if user is the project creator (optional - you can remove this if needed)
    # if project.created_by_id == current_user.id and current_user.role.value not in ["professor", "admin"]:
    #     raise HTTPException(status_code=403, detail="Project creator cannot unenroll")
    
    db.delete(member)
    db.commit()
    
    return None


@router.delete("/{project_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_project_member(
    project_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Remove a member from a project."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Check authorization
    if current_user.role.value not in ["professor", "admin"]:
        member = db.query(ProjectMember).filter(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == current_user.id
        ).first()
        if not member or member.role != "leader":
            raise HTTPException(status_code=403, detail="Only project leaders can remove members")
    
    member = db.query(ProjectMember).filter(
        ProjectMember.project_id == project_id,
        ProjectMember.user_id == user_id
    ).first()
    
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    
    db.delete(member)
    db.commit()
    
    return None


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete a project. Only professors can delete projects. All related tasks will be deleted."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Check authorization - only professors can delete projects
    if current_user.role.value not in ["professor", "admin"]:
        raise HTTPException(status_code=403, detail="Only professors can delete projects")
    
    # Delete the project - cascade will automatically delete:
    # - All tasks (cascade="all, delete-orphan")
    # - All project members (cascade="all, delete-orphan")
    # - All documents (cascade="all, delete-orphan")
    # - All chat messages (cascade="all, delete-orphan")
    # - All meetings (cascade="all, delete-orphan")
    # - All assessments (cascade="all, delete-orphan")
    db.delete(project)
    db.commit()
    
    return None

