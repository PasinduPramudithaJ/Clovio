import os
from typing import List, Dict
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


async def extract_skills_from_text(text: str) -> List[Dict[str, str]]:
    """
    Extract skills from user-provided text using OpenAI.
    Returns a list of skills with categories and levels.
    """
    if not OPENAI_API_KEY:
        # Fallback to basic keyword extraction if API key not available
        return _basic_skill_extraction(text)

    try:
        prompt = f"""
        Analyze the following text and extract technical and soft skills mentioned.
        For each skill, determine:
        1. Skill name
        2. Category (technical, soft, domain)
        3. Proficiency level (beginner, intermediate, advanced, expert)
        
        Text: {text}
        
        Return a JSON array of objects with keys: name, category, level
        """
        
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=OPENAI_API_KEY)
        response = await client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a skill extraction assistant. Return only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=500
        )
        
        import json
        result = response.choices[0].message.content
        if result:
            skills = json.loads(result)
            return skills if isinstance(skills, list) else []
        return []
    
    except Exception as e:
        print(f"Error extracting skills: {e}")
        return _basic_skill_extraction(text)


def _basic_skill_extraction(text: str) -> List[Dict[str, str]]:
    """Fallback basic skill extraction using keyword matching."""
    common_skills = {
        "python": {"category": "technical", "level": "intermediate"},
        "javascript": {"category": "technical", "level": "intermediate"},
        "java": {"category": "technical", "level": "intermediate"},
        "react": {"category": "technical", "level": "intermediate"},
        "sql": {"category": "technical", "level": "intermediate"},
        "communication": {"category": "soft", "level": "intermediate"},
        "leadership": {"category": "soft", "level": "intermediate"},
        "teamwork": {"category": "soft", "level": "intermediate"},
    }
    
    text_lower = text.lower()
    extracted = []
    for skill, details in common_skills.items():
        if skill in text_lower:
            extracted.append({
                "name": skill.title(),
                "category": details["category"],
                "level": details["level"]
            })
    
    return extracted


async def analyze_project_requirements(description: str) -> Dict:
    """
    Analyze project description to identify required skills and complexity.
    """
    if not OPENAI_API_KEY:
        return {
            "required_skills": [],
            "complexity": "medium",
            "estimated_tasks": 5
        }

    try:
        prompt = f"""
        Analyze this project description and identify:
        1. Required technical and soft skills
        2. Project complexity (low, medium, high)
        3. Estimated number of tasks
        
        Project: {description}
        
        Return JSON with keys: required_skills (array), complexity (string), estimated_tasks (number)
        """
        
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=OPENAI_API_KEY)
        response = await client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a project analysis assistant. Return only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )
        
        import json
        result = response.choices[0].message.content
        if result:
            return json.loads(result)
        return {
            "required_skills": [],
            "complexity": "medium",
            "estimated_tasks": 5
        }
    
    except Exception as e:
        print(f"Error analyzing project: {e}")
        return {
            "required_skills": [],
            "complexity": "medium",
            "estimated_tasks": 5
        }

