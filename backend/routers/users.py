from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from models import User, Skill
from schemas import UserResponse, SkillCreate, SkillResponse
from auth import get_current_active_user, require_professor, require_admin

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("/", response_model=List[UserResponse])
async def get_users(
    skip: int = 0,
    limit: int = 100,
    role: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get list of users. Admin can see all users. Professors can see all users. Students can only see themselves."""
    query = db.query(User)
    
    if role:
        query = query.filter(User.role == role)
    
    if current_user.role.value not in ["professor", "admin"]:
        # Students can only see themselves
        query = query.filter(User.id == current_user.id)
    
    users = query.offset(skip).limit(limit).all()
    return users


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get user by ID."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Users can only see their own profile unless they're a professor
    if current_user.id != user_id and current_user.role.value not in ["professor", "admin"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    return user


@router.get("/{user_id}/skills", response_model=List[SkillResponse])
async def get_user_skills(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get skills for a user."""
    # Check authorization
    if current_user.id != user_id and current_user.role.value not in ["professor", "admin"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    skills = db.query(Skill).filter(Skill.user_id == user_id).all()
    return skills


@router.post("/{user_id}/skills", response_model=SkillResponse, status_code=status.HTTP_201_CREATED)
async def add_user_skill(
    user_id: int,
    skill_data: SkillCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Add a skill to a user."""
    # Users can only add skills to themselves
    if current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Check if skill already exists
    existing = db.query(Skill).filter(
        Skill.user_id == user_id,
        Skill.name == skill_data.name
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Skill already exists")
    
    skill = Skill(
        user_id=user_id,
        name=skill_data.name,
        category=skill_data.category,
        level=skill_data.level
    )
    
    db.add(skill)
    db.commit()
    db.refresh(skill)
    
    return skill


@router.delete("/{user_id}/skills/{skill_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_skill(
    user_id: int,
    skill_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete a user skill."""
    if current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    skill = db.query(Skill).filter(
        Skill.id == skill_id,
        Skill.user_id == user_id
    ).first()
    
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    
    db.delete(skill)
    db.commit()
    
    return None


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Delete a user. Admin only. Cannot delete admin users."""
    # Get the user to delete
    user_to_delete = db.query(User).filter(User.id == user_id).first()
    if not user_to_delete:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Prevent deleting admin users
    if user_to_delete.role.value == "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot delete admin users"
        )
    
    # Delete the user (cascade will handle related records)
    db.delete(user_to_delete)
    db.commit()
    
    print(f"[ADMIN] User {user_to_delete.email} (ID: {user_id}) deleted by admin {current_user.email}")
    
    return None

