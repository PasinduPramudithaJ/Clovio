from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from models import Assessment, ProjectMember, Project, User
from schemas import AssessmentCreate, AssessmentResponse
from auth import get_current_active_user, require_professor

router = APIRouter(prefix="/api/assessments", tags=["assessments"])


@router.post("/", response_model=AssessmentResponse, status_code=status.HTTP_201_CREATED)
async def create_assessment(
    assessment_data: AssessmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create an assessment for a project member."""
    # Verify project exists
    project = db.query(Project).filter(Project.id == assessment_data.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Verify evaluated user is a project member
    member = db.query(ProjectMember).filter(
        ProjectMember.project_id == assessment_data.project_id,
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
            ProjectMember.project_id == assessment_data.project_id,
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
        Assessment.project_id == assessment_data.project_id,
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
        from datetime import datetime
        existing.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(existing)
        assessment = existing
    else:
        # Create new assessment
        assessment = Assessment(
            project_id=assessment_data.project_id,
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


@router.get("/", response_model=List[AssessmentResponse])
async def get_assessments(
    project_id: int = None,
    evaluated_user_id: int = None,
    evaluation_type: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get assessments with optional filters."""
    query = db.query(Assessment)
    
    if project_id:
        query = query.filter(Assessment.project_id == project_id)
        # Check authorization
        if current_user.role.value not in ["professor", "admin"]:
            member = db.query(ProjectMember).filter(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == current_user.id
            ).first()
            if not member:
                raise HTTPException(status_code=403, detail="Not authorized")
    
    if evaluated_user_id:
        query = query.filter(Assessment.evaluated_user_id == evaluated_user_id)
        # Users can only see their own assessments unless professor
        if evaluated_user_id != current_user.id and current_user.role.value not in ["professor", "admin"]:
            raise HTTPException(status_code=403, detail="Not authorized")
    
    if evaluation_type:
        query = query.filter(Assessment.evaluation_type == evaluation_type)
    
    assessments = query.order_by(Assessment.created_at.desc()).all()
    
    # Get user names
    result = []
    for assessment in assessments:
        evaluated_user = db.query(User).filter(User.id == assessment.evaluated_user_id).first()
        evaluator_user = db.query(User).filter(User.id == assessment.evaluator_id).first()
        result.append({
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
        })
    
    return result


@router.get("/{assessment_id}", response_model=AssessmentResponse)
async def get_assessment(
    assessment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get a specific assessment."""
    assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")
    
    # Check authorization
    if assessment.evaluated_user_id != current_user.id and assessment.evaluator_id != current_user.id:
        if current_user.role.value not in ["professor", "admin"]:
            # Check if user is a project member
            member = db.query(ProjectMember).filter(
                ProjectMember.project_id == assessment.project_id,
                ProjectMember.user_id == current_user.id
            ).first()
            if not member:
                raise HTTPException(status_code=403, detail="Not authorized")
    
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


@router.delete("/{assessment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_assessment(
    assessment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete an assessment."""
    assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")
    
    # Only evaluator or professor can delete
    if assessment.evaluator_id != current_user.id and current_user.role.value not in ["professor", "admin"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    db.delete(assessment)
    db.commit()
    return None

