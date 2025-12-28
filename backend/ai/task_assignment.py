from typing import List, Dict
from sqlalchemy.orm import Session
from models import User, Task, Skill, ProjectMember
import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


async def assign_tasks_intelligently(
    db: Session,
    project_id: int,
    task_ids: List[int]
) -> List[Dict]:
    """
    Use AI to intelligently assign tasks to team members based on their skills.
    """
    # Get all tasks
    tasks = db.query(Task).filter(Task.id.in_(task_ids)).all()
    
    # Get all project members
    members = db.query(ProjectMember).filter(ProjectMember.project_id == project_id).all()
    member_ids = [m.user_id for m in members]
    
    # Get users with their skills
    users = db.query(User).filter(User.id.in_(member_ids)).all()
    
    if not users or not tasks:
        return []
    
    # Build user skill profiles
    user_profiles = []
    for user in users:
        skills = db.query(Skill).filter(Skill.user_id == user.id).all()
        skill_list = [{"name": s.name, "level": s.level, "category": s.category} for s in skills]
        user_profiles.append({
            "user_id": user.id,
            "name": user.full_name,
            "skills": skill_list
        })
    
    # Build task requirements
    task_requirements = []
    for task in tasks:
        task_requirements.append({
            "task_id": task.id,
            "title": task.title,
            "description": task.description or "",
            "required_skills": task.required_skills or []
        })
    
    # Use AI to match tasks to users
    if OPENAI_API_KEY:
        assignments = await _ai_match_tasks(user_profiles, task_requirements)
    else:
        assignments = _basic_match_tasks(user_profiles, task_requirements)
    
    return assignments


async def _ai_match_tasks(
    user_profiles: List[Dict],
    task_requirements: List[Dict]
) -> List[Dict]:
    """Use OpenAI to match tasks to users."""
    try:
        prompt = f"""
        Match the following tasks to team members based on their skills.
        
        Team Members:
        {_format_user_profiles(user_profiles)}
        
        Tasks:
        {_format_task_requirements(task_requirements)}
        
        For each task, assign it to the best matching team member based on:
        1. Required skills match
        2. Skill level proficiency
        3. Balanced workload distribution
        
        Return JSON array with objects: {{"task_id": int, "assigned_to_id": int, "confidence": float (0-1), "reasoning": string}}
        """
        
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=OPENAI_API_KEY)
        response = await client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a task assignment assistant. Match tasks to team members optimally. Return only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=1000
        )
        
        import json
        result = response.choices[0].message.content
        if result:
            assignments = json.loads(result)
            return assignments if isinstance(assignments, list) else []
        return []
    
    except Exception as e:
        print(f"Error in AI task matching: {e}")
        return _basic_match_tasks(user_profiles, task_requirements)


def _basic_match_tasks(
    user_profiles: List[Dict],
    task_requirements: List[Dict]
) -> List[Dict]:
    """Basic matching algorithm based on skill overlap."""
    assignments = []
    user_task_counts = {profile["user_id"]: 0 for profile in user_profiles}
    
    for task in task_requirements:
        best_match = None
        best_score = 0
        
        for user in user_profiles:
            # Calculate skill match score
            required_skills = [s.lower() for s in task["required_skills"]]
            user_skill_names = [s["name"].lower() for s in user["skills"]]
            
            # Count matching skills
            matches = sum(1 for skill in required_skills if skill in user_skill_names)
            score = matches / max(len(required_skills), 1)
            
            # Prefer users with fewer assigned tasks (load balancing)
            load_factor = 1.0 / (user_task_counts[user["user_id"]] + 1)
            final_score = score * 0.7 + load_factor * 0.3
            
            if final_score > best_score:
                best_score = final_score
                best_match = user["user_id"]
        
        if best_match:
            assignments.append({
                "task_id": task["task_id"],
                "assigned_to_id": best_match,
                "confidence": best_score,
                "reasoning": f"Matched based on skill overlap and workload balance"
            })
            user_task_counts[best_match] += 1
    
    return assignments


def _format_user_profiles(profiles: List[Dict]) -> str:
    """Format user profiles for AI prompt."""
    formatted = []
    for profile in profiles:
        skills_str = ", ".join([f"{s['name']} ({s['level']})" for s in profile["skills"]])
        formatted.append(f"- {profile['name']} (ID: {profile['user_id']}): {skills_str}")
    return "\n".join(formatted)


def _format_task_requirements(tasks: List[Dict]) -> str:
    """Format task requirements for AI prompt."""
    formatted = []
    for task in tasks:
        skills_str = ", ".join(task["required_skills"]) if task["required_skills"] else "None specified"
        formatted.append(f"- {task['title']} (ID: {task['task_id']}): Requires {skills_str}")
    return "\n".join(formatted)

