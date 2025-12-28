from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from models import ChatMessage, ProjectMember, Project, User
from schemas import ChatMessageCreate, ChatMessageResponse
from auth import get_current_active_user

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("/", response_model=ChatMessageResponse, status_code=status.HTTP_201_CREATED)
async def send_message(
    message_data: ChatMessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Send a chat message to a project."""
    # Verify project exists and user has access
    project = db.query(Project).filter(Project.id == message_data.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Check authorization
    if current_user.role.value not in ["professor", "admin"]:
        member = db.query(ProjectMember).filter(
            ProjectMember.project_id == message_data.project_id,
            ProjectMember.user_id == current_user.id
        ).first()
        if not member:
            raise HTTPException(status_code=403, detail="Not authorized")
    
    message = ChatMessage(
        project_id=message_data.project_id,
        user_id=current_user.id,
        message=message_data.message
    )
    
    db.add(message)
    db.commit()
    db.refresh(message)
    
    # Get user name for response
    user = db.query(User).filter(User.id == current_user.id).first()
    
    return {
        "id": message.id,
        "project_id": message.project_id,
        "user_id": message.user_id,
        "user_name": user.full_name,
        "message": message.message,
        "created_at": message.created_at
    }


@router.get("/project/{project_id}", response_model=List[ChatMessageResponse])
async def get_messages(
    project_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get chat messages for a project."""
    # Verify project exists and user has access
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
    
    messages = db.query(ChatMessage).filter(
        ChatMessage.project_id == project_id
    ).order_by(ChatMessage.created_at.desc()).offset(skip).limit(limit).all()
    
    # Get user names
    result = []
    for msg in messages:
        user = db.query(User).filter(User.id == msg.user_id).first()
        result.append({
            "id": msg.id,
            "project_id": msg.project_id,
            "user_id": msg.user_id,
            "user_name": user.full_name if user else "Unknown",
            "message": msg.message,
            "created_at": msg.created_at
        })
    
    return result

