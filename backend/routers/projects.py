from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional
from database import get_db
from models import Project, ProjectMember, Task, Document, ChatMessage, User, Assessment, Meeting, MeetingParticipant, Contribution
from schemas import (
    ProjectCreate, ProjectResponse, ProjectDetail, TaskResponse,
    DocumentResponse, AssessmentCreate, AssessmentResponse,
    MeetingCreate, MeetingResponse, MeetingDetail,
    ContributionCreate, ContributionResponse
)
from auth import get_current_active_user, require_professor
from ai.task_breakdown import break_down_project
from ai.task_assignment import assign_tasks_intelligently
from datetime import datetime
import os
import uuid
from pathlib import Path
import aiofiles

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.post("/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_data: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new project. Only students can create projects."""
    # Only students can create projects
    if current_user.role.value == "professor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Professors cannot create projects. Only students can create projects."
        )
    
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
    
    # Automatically break down project into tasks based on description
    try:
        deadline_str = project.deadline.isoformat() if isinstance(project.deadline, datetime) else str(project.deadline)
        print(f"[AI Breakdown] Analyzing project description to create tasks for project: {project.title}")
        print(f"[AI Breakdown] Project description length: {len(project.description)} characters")
        task_data_list = await break_down_project(project.description, deadline_str)
        print(f"[AI Breakdown] Generated {len(task_data_list)} tasks from project description")
        
        created_tasks = []
        for task_data in task_data_list:
            task = Task(
                project_id=project.id,
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
        
        # Refresh tasks to get their IDs
        for task in created_tasks:
            db.refresh(task)
        
        # Automatically assign tasks to enrolled members based on their skills
        if created_tasks:
            # Get all enrolled member IDs from the database (including creator and any added members)
            members = db.query(ProjectMember).filter(ProjectMember.project_id == project.id).all()
            
            # Only assign if there are members enrolled (there should always be at least the creator)
            if len(members) > 0:
                task_ids = [task.id for task in created_tasks]
                try:
                    assignments = await assign_tasks_intelligently(db, project.id, task_ids)
                    
                    # Apply assignments
                    for assignment in assignments:
                        task = db.query(Task).filter(Task.id == assignment["task_id"]).first()
                        if task:
                            task.assigned_to_id = assignment["assigned_to_id"]
                    
                    db.commit()
                except Exception as e:
                    # If assignment fails, tasks remain unassigned (can be assigned manually later)
                    print(f"Warning: Could not auto-assign tasks: {e}")
    
    except Exception as e:
        # If task breakdown fails, project is still created but without tasks
        # Tasks can be created manually later using the breakdown endpoint
        print(f"Warning: Could not auto-create tasks from project description: {e}")
        # Project is already committed, so we don't need to rollback or re-commit
    
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
    
    # Get members with their roles
    members = db.query(ProjectMember).filter(ProjectMember.project_id == project_id).all()
    member_data = []
    for member in members:
        user = db.query(User).filter(User.id == member.user_id).first()
        if user:
            # Create member dict with user data and project member role
            member_dict = {
                "id": user.id,
                "email": user.email,
                "full_name": user.full_name,
                "role": user.role.value,  # User role (student/professor/admin)
                "student_id": user.student_id,
                "department": user.department,
                "year_level": user.year_level,
                "is_active": user.is_active,
                "is_verified": user.is_verified,
                "created_at": user.created_at,
                "member_role": member.role  # Project member role (leader or member)
            }
            member_data.append(member_dict)
    
    # Get tasks - only show if user is enrolled (or is professor)
    if is_enrolled:
        tasks = db.query(Task).filter(Task.project_id == project_id).all()
    else:
        tasks = []  # Empty list if not enrolled
    
    # Get document count
    try:
        doc_count = db.query(Document).filter(Document.project_id == project_id).count()
    except Exception:
        doc_count = 0
    
    # Get message count
    try:
        msg_count = db.query(ChatMessage).filter(ChatMessage.project_id == project_id).count()
    except Exception:
        msg_count = 0
    
    # Get assessment count
    try:
        assessment_count = db.query(Assessment).filter(Assessment.project_id == project_id).count()
    except Exception:
        assessment_count = 0
    
    # Get meeting count
    try:
        meeting_count = db.query(Meeting).filter(Meeting.project_id == project_id).count()
    except Exception as e:
        # If meeting_room_url column doesn't exist, try to handle gracefully
        print(f"Warning: Could not get meeting count: {e}")
        meeting_count = 0
    
    # Get contribution count
    try:
        contribution_count = db.query(Contribution).filter(Contribution.project_id == project_id).count()
    except Exception:
        contribution_count = 0
    
    # Build response with all required fields
    # Handle None values properly for optional fields
    response_data = {
        "id": project.id,
        "title": project.title,
        "description": project.description,
        "course_code": project.course_code if project.course_code else None,
        "course_name": project.course_name if project.course_name else None,
        "deadline": project.deadline,
        "created_by_id": project.created_by_id,
        "status": project.status if project.status else "active",
        "ai_assigned": project.ai_assigned if project.ai_assigned is not None else False,
        "created_at": project.created_at,
        "updated_at": project.updated_at if project.updated_at else None,
        "members": member_data,
        "tasks": tasks,
        "document_count": doc_count,
        "message_count": msg_count,
        "assessment_count": assessment_count,
        "meeting_count": meeting_count,
        "contribution_count": contribution_count
    }
    
    return response_data


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
    
    # Use AI to break down project based on description
    deadline_str = project.deadline.isoformat() if isinstance(project.deadline, datetime) else str(project.deadline)
    print(f"[AI Breakdown] Manual breakdown requested for project: {project.title}")
    print(f"[AI Breakdown] Analyzing project description: {project.description[:100]}...")
    task_data_list = await break_down_project(project.description, deadline_str)
    print(f"[AI Breakdown] Generated {len(task_data_list)} tasks from project description")
    
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


@router.post("/{project_id}/documents/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_project_document(
    project_id: int,
    file: UploadFile = File(...),
    description: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Upload a document to a project."""
    # Verify project exists
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
            raise HTTPException(status_code=403, detail="Not authorized to upload documents to this project")
    
    # Create uploads directory if it doesn't exist
    upload_dir = Path("uploads")
    upload_dir.mkdir(exist_ok=True)
    
    # Generate unique filename
    file_ext = Path(file.filename).suffix
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    file_path = upload_dir / unique_filename
    
    # Save file
    async with aiofiles.open(file_path, 'wb') as f:
        content = await file.read()
        await f.write(content)
    
    # Get file size
    file_size = os.path.getsize(file_path)
    
    # Create document record
    document = Document(
        project_id=project_id,
        uploaded_by_id=current_user.id,
        filename=unique_filename,
        original_filename=file.filename,
        file_path=str(file_path),
        file_size=file_size,
        file_type=file.content_type or "application/octet-stream",
        description=description
    )
    
    db.add(document)
    db.commit()
    db.refresh(document)
    
    return document


@router.post("/{project_id}/assessments", response_model=AssessmentResponse, status_code=status.HTTP_201_CREATED)
async def create_project_assessment(
    project_id: int,
    assessment_data: AssessmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create an assessment for a project member."""
    # Verify project exists
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Ensure the assessment is for this project
    if assessment_data.project_id != project_id:
        raise HTTPException(status_code=400, detail="Project ID mismatch")
    
    # Verify evaluated user is a project member
    member = db.query(ProjectMember).filter(
        ProjectMember.project_id == project_id,
        ProjectMember.user_id == assessment_data.evaluated_user_id
    ).first()
    if not member:
        raise HTTPException(status_code=400, detail="User is not a project member")
    
    # Check authorization based on evaluation type
    if assessment_data.evaluation_type == "professor":
        if current_user.role.value not in ["professor", "admin"]:
            raise HTTPException(status_code=403, detail="Only professors can create professor assessments")
    elif assessment_data.evaluation_type == "peer":
        # Peers must be project members
        evaluator_member = db.query(ProjectMember).filter(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == current_user.id
        ).first()
        if not evaluator_member:
            raise HTTPException(status_code=403, detail="Must be a project member to create peer assessment")
        if assessment_data.evaluated_user_id == current_user.id:
            raise HTTPException(status_code=400, detail="Cannot create peer assessment for yourself")
    elif assessment_data.evaluation_type == "self":
        if assessment_data.evaluated_user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Can only create self-assessment for yourself")
    
    # Check if assessment already exists
    existing = db.query(Assessment).filter(
        Assessment.project_id == project_id,
        Assessment.evaluated_user_id == assessment_data.evaluated_user_id,
        Assessment.evaluator_id == current_user.id,
        Assessment.evaluation_type == assessment_data.evaluation_type
    ).first()
    
    if existing:
        # Update existing assessment
        existing.overall_score = assessment_data.overall_score
        existing.technical_skills = assessment_data.technical_skills
        existing.collaboration = assessment_data.collaboration
        existing.communication = assessment_data.communication
        existing.problem_solving = assessment_data.problem_solving
        existing.comments = assessment_data.comments
        existing.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(existing)
        assessment = existing
    else:
        # Create new assessment
        assessment = Assessment(
            project_id=project_id,
            evaluated_user_id=assessment_data.evaluated_user_id,
            evaluator_id=current_user.id,
            evaluation_type=assessment_data.evaluation_type,
            overall_score=assessment_data.overall_score,
            technical_skills=assessment_data.technical_skills,
            collaboration=assessment_data.collaboration,
            communication=assessment_data.communication,
            problem_solving=assessment_data.problem_solving,
            comments=assessment_data.comments
        )
        db.add(assessment)
        db.commit()
        db.refresh(assessment)
    
    # Get user names for response
    evaluated_user = db.query(User).filter(User.id == assessment.evaluated_user_id).first()
    evaluator_user = db.query(User).filter(User.id == assessment.evaluator_id).first()
    
    return {
        "id": assessment.id,
        "project_id": assessment.project_id,
        "evaluated_user_id": assessment.evaluated_user_id,
        "evaluated_user_name": evaluated_user.full_name if evaluated_user else "Unknown",
        "evaluator_id": assessment.evaluator_id,
        "evaluator_name": evaluator_user.full_name if evaluator_user else "Unknown",
        "evaluation_type": assessment.evaluation_type,
        "overall_score": assessment.overall_score,
        "technical_skills": assessment.technical_skills,
        "collaboration": assessment.collaboration,
        "communication": assessment.communication,
        "problem_solving": assessment.problem_solving,
        "comments": assessment.comments,
        "created_at": assessment.created_at,
        "updated_at": assessment.updated_at
    }


@router.post("/{project_id}/meetings", response_model=MeetingResponse, status_code=status.HTTP_201_CREATED)
async def create_project_meeting(
    project_id: int,
    meeting_data: MeetingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a meeting for a project."""
    # Verify project exists
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Ensure the meeting is for this project
    if meeting_data.project_id != project_id:
        raise HTTPException(status_code=400, detail="Project ID mismatch")
    
    # Check authorization
    if current_user.role.value not in ["professor", "admin"]:
        member = db.query(ProjectMember).filter(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == current_user.id
        ).first()
        if not member:
            raise HTTPException(status_code=403, detail="Not authorized to create meetings for this project")
    
    # Generate meeting room URL if virtual/hybrid and not provided
    meeting_room_url = meeting_data.meeting_room_url
    if not meeting_room_url and meeting_data.meeting_type in ["virtual", "hybrid"]:
        # Generate a unique room ID for WebRTC
        import uuid
        room_id = f"meeting_{project_id}_{uuid.uuid4().hex[:12]}"
        meeting_room_url = room_id
    
    # Create meeting
    meeting = Meeting(
        project_id=project_id,
        title=meeting_data.title,
        description=meeting_data.description,
        start_time=meeting_data.start_time,
        end_time=meeting_data.end_time,
        location=meeting_data.location,
        meeting_type=meeting_data.meeting_type,
        meeting_room_url=meeting_room_url,
        created_by_id=current_user.id
    )
    db.add(meeting)
    db.commit()
    db.refresh(meeting)
    
    # Add participants
    participant_ids = meeting_data.participant_ids if meeting_data.participant_ids else []
    # If no participants specified, add all project members
    if not participant_ids:
        members = db.query(ProjectMember).filter(
            ProjectMember.project_id == project_id
        ).all()
        participant_ids = [m.user_id for m in members]
    
    for user_id in participant_ids:
        # Verify user is a project member
        member = db.query(ProjectMember).filter(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user_id
        ).first()
        if member:
            participant = MeetingParticipant(
                meeting_id=meeting.id,
                user_id=user_id,
                status="pending"
            )
            db.add(participant)
    
    db.commit()
    
    return meeting


@router.get("/{project_id}/meetings", response_model=List[MeetingResponse])
async def get_project_meetings(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get all meetings for a project."""
    # Verify project exists
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
    
    meetings = db.query(Meeting).filter(Meeting.project_id == project_id).order_by(Meeting.start_time.desc()).all()
    return meetings


@router.post("/{project_id}/contributions", response_model=ContributionResponse, status_code=status.HTTP_201_CREATED)
async def create_project_contribution(
    project_id: int,
    contribution_data: ContributionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Record a contribution to a project."""
    # Verify project exists
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Ensure the contribution is for this project
    if contribution_data.project_id != project_id:
        raise HTTPException(status_code=400, detail="Project ID mismatch")
    
    # Check authorization - user must be a project member
    if current_user.role.value not in ["professor", "admin"]:
        member = db.query(ProjectMember).filter(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == current_user.id
        ).first()
        if not member:
            raise HTTPException(status_code=403, detail="Not authorized to record contributions for this project")
    
    # Users can only record their own contributions
    if contribution_data.user_id and contribution_data.user_id != current_user.id:
        if current_user.role.value not in ["professor", "admin"]:
            raise HTTPException(status_code=403, detail="Can only record your own contributions")
    
    contribution = Contribution(
        project_id=project_id,
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


@router.get("/{project_id}/contributions", response_model=List[ContributionResponse])
async def get_project_contributions(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get all contributions for a project."""
    # Verify project exists
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
    
    contributions = db.query(Contribution).filter(
        Contribution.project_id == project_id
    ).order_by(Contribution.created_at.desc()).all()
    
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


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete a project. Only admins can delete projects. Professors cannot delete projects."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Check authorization - only admins can delete projects (not professors)
    if current_user.role.value != "admin":
        if current_user.role.value == "professor":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Professors cannot delete projects. Only admins can delete projects."
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admins can delete projects"
            )
    
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

