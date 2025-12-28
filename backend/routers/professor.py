from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from models import Project, Task

router = APIRouter(prefix="/professor")

@router.get("/overview")
def overview(db: Session = Depends(get_db)):
    return {
        "projects": db.query(Project).count(),
        "tasks": db.query(Task).count()
    }
