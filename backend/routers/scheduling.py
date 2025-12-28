from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from models import UserAvailability, Meeting, MeetingParticipant, ProjectMember, Project, User
from schemas import (
    UserAvailabilityCreate, UserAvailabilityResponse,
    MeetingCreate, MeetingResponse, MeetingDetail, MeetingParticipantResponse
)
from auth import get_current_active_user

router = APIRouter(prefix="/api/scheduling", tags=["scheduling"])


@router.post("/availability", response_model=UserAvailabilityResponse, status_code=status.HTTP_201_CREATED)
async def set_availability(
    availability_data: UserAvailabilityCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Set user availability for scheduling."""
    # Check if availability already exists for this day
    existing = db.query(UserAvailability).filter(
        UserAvailability.user_id == current_user.id,
        UserAvailability.day_of_week == availability_data.day_of_week
    ).first()
    
    if existing:
        # Update existing
        existing.start_time = availability_data.start_time
        existing.end_time = availability_data.end_time
        existing.timezone = availability_data.timezone
    else:
        # Create new
        availability = UserAvailability(
            user_id=current_user.id,
            day_of_week=availability_data.day_of_week,
            start_time=availability_data.start_time,
            end_time=availability_data.end_time,
            timezone=availability_data.timezone
        )
        db.add(availability)
    
    db.commit()
    db.refresh(existing if existing else availability)
    return existing if existing else availability


@router.get("/availability", response_model=List[UserAvailabilityResponse])
async def get_availability(
    user_id: int = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get availability for a user or current user."""
    target_user_id = user_id if user_id else current_user.id
    
    # Check authorization
    if target_user_id != current_user.id and current_user.role.value not in ["professor", "admin"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    availability = db.query(UserAvailability).filter(
        UserAvailability.user_id == target_user_id
    ).all()
    
    return availability


@router.delete("/availability/{availability_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_availability(
    availability_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete availability entry."""
    availability = db.query(UserAvailability).filter(
        UserAvailability.id == availability_id,
        UserAvailability.user_id == current_user.id
    ).first()
    
    if not availability:
        raise HTTPException(status_code=404, detail="Availability not found")
    
    db.delete(availability)
    db.commit()
    return None


@router.post("/meetings", response_model=MeetingResponse, status_code=status.HTTP_201_CREATED)
async def create_meeting(
    meeting_data: MeetingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a meeting for a project."""
    # Verify project exists and user has access
    project = db.query(Project).filter(Project.id == meeting_data.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Check authorization
    if current_user.role.value not in ["professor", "admin"]:
        member = db.query(ProjectMember).filter(
            ProjectMember.project_id == meeting_data.project_id,
            ProjectMember.user_id == current_user.id
        ).first()
        if not member:
            raise HTTPException(status_code=403, detail="Not authorized")
    
    # Generate meeting room URL if virtual/hybrid and not provided
    meeting_room_url = meeting_data.meeting_room_url
    if not meeting_room_url and meeting_data.meeting_type in ["virtual", "hybrid"]:
        # Generate a simple room URL (in production, integrate with video service API)
        import uuid
        room_id = str(uuid.uuid4())[:8]
        meeting_room_url = f"/meeting/{room_id}"
    
    # Create meeting
    meeting = Meeting(
        project_id=meeting_data.project_id,
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
            ProjectMember.project_id == meeting_data.project_id
        ).all()
        participant_ids = [m.user_id for m in members]
    
    for user_id in participant_ids:
        participant = MeetingParticipant(
            meeting_id=meeting.id,
            user_id=user_id,
            status="pending"
        )
        db.add(participant)
    
    db.commit()
    
    return meeting


@router.get("/meetings/project/{project_id}", response_model=List[MeetingResponse])
async def get_project_meetings(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get all meetings for a project."""
    # Check authorization
    if current_user.role.value not in ["professor", "admin"]:
        member = db.query(ProjectMember).filter(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == current_user.id
        ).first()
        if not member:
            raise HTTPException(status_code=403, detail="Not authorized")
    
    meetings = db.query(Meeting).filter(Meeting.project_id == project_id).all()
    return meetings


@router.get("/meetings/{meeting_id}", response_model=MeetingDetail)
async def get_meeting(
    meeting_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get meeting details with participants."""
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    
    # Check authorization
    if current_user.role.value not in ["professor", "admin"]:
        member = db.query(ProjectMember).filter(
            ProjectMember.project_id == meeting.project_id,
            ProjectMember.user_id == current_user.id
        ).first()
        if not member:
            raise HTTPException(status_code=403, detail="Not authorized")
    
    # Get participants
    participants = db.query(MeetingParticipant).filter(
        MeetingParticipant.meeting_id == meeting_id
    ).all()
    
    participant_responses = []
    for p in participants:
        user = db.query(User).filter(User.id == p.user_id).first()
        participant_responses.append({
            "id": p.id,
            "meeting_id": p.meeting_id,
            "user_id": p.user_id,
            "user_name": user.full_name if user else "Unknown",
            "status": p.status,
            "responded_at": p.responded_at
        })
    
    return {
        **meeting.__dict__,
        "participants": participant_responses
    }


@router.patch("/meetings/{meeting_id}/participants/{user_id}", response_model=MeetingParticipantResponse)
async def update_participant_status(
    meeting_id: int,
    user_id: int,
    status: str,  # accepted, declined, tentative
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update meeting participant status."""
    if current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Can only update your own status")
    
    participant = db.query(MeetingParticipant).filter(
        MeetingParticipant.meeting_id == meeting_id,
        MeetingParticipant.user_id == user_id
    ).first()
    
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")
    
    participant.status = status
    from datetime import datetime
    participant.responded_at = datetime.utcnow()
    
    db.commit()
    db.refresh(participant)
    
    user = db.query(User).filter(User.id == user_id).first()
    return {
        "id": participant.id,
        "meeting_id": participant.meeting_id,
        "user_id": participant.user_id,
        "user_name": user.full_name if user else "Unknown",
        "status": participant.status,
        "responded_at": participant.responded_at
    }


@router.delete("/meetings/{meeting_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_meeting(
    meeting_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete a meeting."""
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    
    # Only creator or professor can delete
    if meeting.created_by_id != current_user.id and current_user.role.value not in ["professor", "admin"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    db.delete(meeting)
    db.commit()
    return None

