from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class UserRole(str, Enum):
    STUDENT = "student"
    PROFESSOR = "professor"
    ADMIN = "admin"


class TaskStatus(str, Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    COMPLETED = "completed"
    BLOCKED = "blocked"


# User Schemas
class UserBase(BaseModel):
    email: EmailStr
    full_name: str
    role: UserRole = UserRole.STUDENT
    student_id: Optional[str] = None
    department: Optional[str] = None
    year_level: Optional[int] = None


class UserCreate(UserBase):
    password: str  # No length restrictions - backend handles any password length via SHA256 pre-hashing


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(UserBase):
    id: int
    is_active: bool
    is_verified: bool
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse


# Skill Schemas
class SkillBase(BaseModel):
    name: str
    category: str
    level: str


class SkillCreate(SkillBase):
    pass


class SkillResponse(SkillBase):
    id: int
    user_id: int
    verified: bool
    created_at: datetime

    class Config:
        from_attributes = True


# Project Schemas
class ProjectBase(BaseModel):
    title: str
    description: str
    course_code: Optional[str] = None
    course_name: Optional[str] = None
    deadline: datetime


class ProjectCreate(ProjectBase):
    member_ids: Optional[List[int]] = []


class ProjectResponse(ProjectBase):
    id: int
    created_by_id: int
    status: str
    ai_assigned: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ProjectDetail(ProjectResponse):
    members: List[UserResponse]
    tasks: List["TaskResponse"]
    document_count: int
    message_count: int


# Task Schemas
class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    priority: str = "medium"
    required_skills: Optional[List[str]] = []
    estimated_hours: Optional[float] = None
    due_date: Optional[datetime] = None


class TaskCreate(TaskBase):
    project_id: int
    assigned_to_id: Optional[int] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[TaskStatus] = None
    priority: Optional[str] = None
    assigned_to_id: Optional[int] = None
    actual_hours: Optional[float] = None
    due_date: Optional[datetime] = None


class TimeLogCreate(BaseModel):
    task_id: int
    hours: float
    description: Optional[str] = None
    date: Optional[datetime] = None  # Optional date, defaults to now


class TimeLogResponse(BaseModel):
    id: int
    task_id: int
    user_id: int
    user_name: str
    hours: float
    description: Optional[str] = None
    logged_date: datetime
    created_at: datetime

    class Config:
        from_attributes = True


class TaskResponse(TaskBase):
    id: int
    project_id: int
    status: TaskStatus
    assigned_to_id: Optional[int] = None
    actual_hours: float
    created_at: datetime
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Document Schemas
class DocumentBase(BaseModel):
    description: Optional[str] = None


class DocumentCreate(DocumentBase):
    project_id: int


class DocumentResponse(DocumentBase):
    id: int
    project_id: int
    uploaded_by_id: int
    filename: str
    original_filename: str
    file_size: int
    file_type: str
    version: int
    created_at: datetime

    class Config:
        from_attributes = True


# Chat Schemas
class ChatMessageCreate(BaseModel):
    project_id: int
    message: str


class ChatMessageResponse(BaseModel):
    id: int
    project_id: int
    user_id: int
    user_name: str
    message: str
    created_at: datetime

    class Config:
        from_attributes = True


# Contribution Schemas
class ContributionCreate(BaseModel):
    project_id: int
    task_id: Optional[int] = None
    contribution_type: str
    description: str
    hours_spent: float = 0.0
    user_id: Optional[int] = None  # Optional, defaults to current user


class ContributionResponse(BaseModel):
    id: int
    project_id: int
    user_id: int
    user_name: str
    task_id: Optional[int] = None
    contribution_type: str
    description: str
    hours_spent: float
    created_at: datetime

    class Config:
        from_attributes = True


# Analytics Schemas
class ProjectAnalytics(BaseModel):
    project_id: int
    total_tasks: int
    completed_tasks: int
    in_progress_tasks: int
    total_hours: float
    member_contributions: List[dict]
    skill_distribution: dict


class UserAnalytics(BaseModel):
    user_id: int
    total_projects: int
    completed_tasks: int
    total_hours: float
    skills_developed: List[str]
    contribution_breakdown: dict


# AI Task Assignment
class AITaskAssignmentRequest(BaseModel):
    project_id: int
    task_ids: List[int]


class AITaskAssignmentResponse(BaseModel):
    assignments: List[dict]  # [{task_id: int, assigned_to_id: int, confidence: float}]


# Scheduling Schemas
class UserAvailabilityBase(BaseModel):
    day_of_week: int  # 0-6 (Monday-Sunday)
    start_time: str  # HH:MM format
    end_time: str  # HH:MM format
    timezone: str = "UTC"


class UserAvailabilityCreate(UserAvailabilityBase):
    pass


class UserAvailabilityResponse(UserAvailabilityBase):
    id: int
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True


# Meeting Schemas
class MeetingBase(BaseModel):
    title: str
    description: Optional[str] = None
    start_time: datetime
    end_time: datetime
    location: Optional[str] = None
    meeting_type: str = "virtual"  # virtual, in_person, hybrid


class MeetingCreate(MeetingBase):
    project_id: int
    participant_ids: List[int] = []


class MeetingResponse(MeetingBase):
    id: int
    project_id: int
    created_by_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class MeetingParticipantResponse(BaseModel):
    id: int
    meeting_id: int
    user_id: int
    user_name: str
    status: str
    responded_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class MeetingDetail(MeetingResponse):
    participants: List[MeetingParticipantResponse]


# Assessment Schemas
class AssessmentBase(BaseModel):
    overall_score: float  # 0-100
    technical_skills: Optional[float] = None
    collaboration: Optional[float] = None
    communication: Optional[float] = None
    problem_solving: Optional[float] = None
    comments: Optional[str] = None


class AssessmentCreate(AssessmentBase):
    project_id: int
    evaluated_user_id: int
    evaluation_type: str  # professor, peer, self


class AssessmentResponse(AssessmentBase):
    id: int
    project_id: int
    evaluated_user_id: int
    evaluated_user_name: str
    evaluator_id: int
    evaluator_name: str
    evaluation_type: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Contribution Schemas (enhanced)
class ContributionResponse(BaseModel):
    id: int
    project_id: int
    user_id: int
    user_name: str
    task_id: Optional[int] = None
    contribution_type: str
    description: str
    hours_spent: float
    created_at: datetime

    class Config:
        from_attributes = True


# Learning Analytics Schemas (enhanced)
class LearningAnalyticsCreate(BaseModel):
    project_id: Optional[int] = None
    skill_developed: str
    proficiency_level: str  # beginner, intermediate, advanced, expert
    evidence: Optional[str] = None


class LearningAnalyticsResponse(BaseModel):
    id: int
    user_id: int
    project_id: Optional[int] = None
    skill_developed: str
    proficiency_level: str
    evidence: Optional[str] = None
    recorded_at: datetime

    class Config:
        from_attributes = True


# Update forward references
ProjectDetail.model_rebuild()
TaskResponse.model_rebuild()

