from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from models import Task, ProjectMember, Project, User, TimeLog
from schemas import TaskCreate, TaskResponse, TaskUpdate, TimeLogCreate, TimeLogResponse
from auth import get_current_active_user
from ai.task_assignment import assign_tasks_intelligently
from datetime import datetime

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.post("/", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    task_data: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new task. Students can create tasks and assign them to themselves."""
    # Verify project exists and user has access
    project = db.query(Project).filter(Project.id == task_data.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Check authorization - user must be a project member
    if current_user.role.value not in ["professor", "admin"]:
        member = db.query(ProjectMember).filter(
            ProjectMember.project_id == task_data.project_id,
            ProjectMember.user_id == current_user.id
        ).first()
        if not member:
            raise HTTPException(status_code=403, detail="Not authorized - you must be a project member")
        
        # Students can only assign tasks to themselves
        if task_data.assigned_to_id and task_data.assigned_to_id != current_user.id:
            raise HTTPException(status_code=403, detail="Students can only assign tasks to themselves")
    
    # If no assigned_to_id provided and user is a student, assign to themselves
    assigned_to_id = task_data.assigned_to_id
    if not assigned_to_id and current_user.role.value == "student":
        assigned_to_id = current_user.id
    
    task = Task(
        project_id=task_data.project_id,
        title=task_data.title,
        description=task_data.description,
        priority=task_data.priority,
        required_skills=task_data.required_skills,
        estimated_hours=task_data.estimated_hours,
        due_date=task_data.due_date,
        assigned_to_id=assigned_to_id
    )
    
    db.add(task)
    db.commit()
    db.refresh(task)
    
    return task


@router.get("/", response_model=List[TaskResponse])
async def get_tasks(
    project_id: int = None,
    assigned_to_id: int = None,
    status: str = None,
    skip: int = 0,
    limit: int = 10000,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get tasks with optional filters. Tasks are only visible if user is enrolled in the project."""
    # Validate limit doesn't exceed maximum
    if limit > 10000:
        limit = 10000
    
    query = db.query(Task)
    
    if project_id:
        query = query.filter(Task.project_id == project_id)
        # Check if user is enrolled in the project
        if current_user.role.value not in ["professor", "admin"]:
            member = db.query(ProjectMember).filter(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == current_user.id
            ).first()
            if not member:
                # Return empty list instead of error - user can see project but not tasks
                return []
    
    if assigned_to_id:
        query = query.filter(Task.assigned_to_id == assigned_to_id)
        # Users can only see their own assigned tasks unless professor
        if current_user.id != assigned_to_id and current_user.role.value not in ["professor", "admin"]:
            raise HTTPException(status_code=403, detail="Not authorized")
    
    if status:
        query = query.filter(Task.status == status)
    
    # Filter tasks to only show those from projects user is enrolled in (unless professor)
    if current_user.role.value not in ["professor", "admin"]:
        # Get all project IDs user is enrolled in
        member_projects = db.query(ProjectMember).filter(
            ProjectMember.user_id == current_user.id
        ).all()
        enrolled_project_ids = [mp.project_id for mp in member_projects]
        
        if enrolled_project_ids:
            query = query.filter(Task.project_id.in_(enrolled_project_ids))
        else:
            # User is not enrolled in any projects, return empty list
            return []
    
    tasks = query.offset(skip).limit(limit).all()
    return tasks


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get task by ID."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Check authorization
    if current_user.role.value not in ["professor", "admin"]:
        member = db.query(ProjectMember).filter(
            ProjectMember.project_id == task.project_id,
            ProjectMember.user_id == current_user.id
        ).first()
        if not member:
            raise HTTPException(status_code=403, detail="Not authorized")
    
    return task


@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: int,
    task_update: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update a task."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Check authorization - users must be project members
    if current_user.role.value not in ["professor", "admin"]:
        member = db.query(ProjectMember).filter(
            ProjectMember.project_id == task.project_id,
            ProjectMember.user_id == current_user.id
        ).first()
        if not member:
            raise HTTPException(status_code=403, detail="Not authorized")
        
        # Students can only update their own assigned tasks or assign tasks to themselves
        if task_update.assigned_to_id and task_update.assigned_to_id != current_user.id:
            raise HTTPException(status_code=403, detail="Can only assign tasks to yourself")
        
        # If task is assigned to someone else, only allow status updates
        if task.assigned_to_id and task.assigned_to_id != current_user.id:
            # Only allow status updates for tasks assigned to others
            update_data = task_update.dict(exclude_unset=True)
            allowed_fields = {"status"}
            for field in list(update_data.keys()):
                if field not in allowed_fields:
                    del update_data[field]
        else:
            update_data = task_update.dict(exclude_unset=True)
    else:
        # Professors can update anything
        update_data = task_update.dict(exclude_unset=True)
    
    # Apply updates
    for field, value in update_data.items():
        setattr(task, field, value)
    
    # Update completed_at if status is completed
    if task_update.status and task_update.status.value == "completed":
        task.completed_at = datetime.utcnow()
    
    db.commit()
    db.refresh(task)
    
    return task


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete a task."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Check authorization - only professors or project leaders can delete
    if current_user.role.value not in ["professor", "admin"]:
        member = db.query(ProjectMember).filter(
            ProjectMember.project_id == task.project_id,
            ProjectMember.user_id == current_user.id
        ).first()
        if not member or member.role != "leader":
            raise HTTPException(status_code=403, detail="Not authorized")
    
    db.delete(task)
    db.commit()
    
    return None


@router.post("/assign-ai", response_model=List[dict])
async def assign_tasks_ai(
    project_id: int,
    task_ids: List[int],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Use AI to intelligently assign tasks to team members."""
    # Check authorization - only professors can use AI assignment
    if current_user.role.value not in ["professor", "admin"]:
        raise HTTPException(status_code=403, detail="Only professors can use AI assignment")
    
    assignments = await assign_tasks_intelligently(db, project_id, task_ids)
    
    # Apply assignments
    for assignment in assignments:
        task = db.query(Task).filter(Task.id == assignment["task_id"]).first()
        if task:
            task.assigned_to_id = assignment["assigned_to_id"]
    
    db.commit()
    
    return assignments


@router.post("/log-time", response_model=TimeLogResponse, status_code=status.HTTP_201_CREATED)
async def log_time(
    time_log_data: TimeLogCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Log time spent on a task."""
    # Verify task exists
    task = db.query(Task).filter(Task.id == time_log_data.task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Check authorization - user must be a project member
    if current_user.role.value not in ["professor", "admin"]:
        member = db.query(ProjectMember).filter(
            ProjectMember.project_id == task.project_id,
            ProjectMember.user_id == current_user.id
        ).first()
        if not member:
            raise HTTPException(status_code=403, detail="Not authorized to log time for this task")
    
    # Create time log entry
    time_log = TimeLog(
        task_id=time_log_data.task_id,
        user_id=current_user.id,
        hours=time_log_data.hours,
        description=time_log_data.description,
        logged_date=time_log_data.date if time_log_data.date else datetime.utcnow()
    )
    
    db.add(time_log)
    
    # Update task's actual_hours
    task.actual_hours = (task.actual_hours or 0.0) + time_log_data.hours
    
    db.commit()
    db.refresh(time_log)
    
    # Get user name for response
    user = db.query(User).filter(User.id == current_user.id).first()
    
    return {
        "id": time_log.id,
        "task_id": time_log.task_id,
        "user_id": time_log.user_id,
        "user_name": user.full_name if user else "Unknown",
        "hours": time_log.hours,
        "description": time_log.description,
        "logged_date": time_log.logged_date,
        "created_at": time_log.created_at
    }


@router.get("/{task_id}/time-logs", response_model=List[TimeLogResponse])
async def get_task_time_logs(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get time logs for a task."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Check authorization
    if current_user.role.value not in ["professor", "admin"]:
        member = db.query(ProjectMember).filter(
            ProjectMember.project_id == task.project_id,
            ProjectMember.user_id == current_user.id
        ).first()
        if not member:
            raise HTTPException(status_code=403, detail="Not authorized")
    
    time_logs = db.query(TimeLog).filter(TimeLog.task_id == task_id).order_by(TimeLog.logged_date.desc()).all()
    
    # Get user names
    result = []
    for log in time_logs:
        user = db.query(User).filter(User.id == log.user_id).first()
        result.append({
            "id": log.id,
            "task_id": log.task_id,
            "user_id": log.user_id,
            "user_name": user.full_name if user else "Unknown",
            "hours": log.hours,
            "description": log.description,
            "logged_date": log.logged_date,
            "created_at": log.created_at
        })
    
    return result

