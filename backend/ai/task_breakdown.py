import os
from typing import List, Dict
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


async def break_down_project(project_description: str, deadline: str) -> List[Dict]:
    """
    Break down a project into individual tasks using AI.
    """
    if not OPENAI_API_KEY:
        return _basic_task_breakdown(project_description)

    try:
        prompt = f"""
        Break down the following project into specific, actionable tasks.
        Each task should have:
        - title: Clear, specific task name
        - description: Detailed description of what needs to be done
        - priority: low, medium, high, or urgent
        - estimated_hours: Estimated hours to complete
        - required_skills: List of skills needed (e.g., ["Python", "SQL", "API Design"])
        
        Project Description: {project_description}
        Deadline: {deadline}
        
        Return a JSON array of task objects. Create 5-10 tasks that cover all aspects of the project.
        """
        
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=OPENAI_API_KEY)
        response = await client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a project management assistant. Break down projects into actionable tasks. Return only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.4,
            max_tokens=1500
        )
        
        import json
        result = response.choices[0].message.content
        if result:
            tasks = json.loads(result)
            return tasks if isinstance(tasks, list) else []
        return []
    
    except Exception as e:
        print(f"Error breaking down project: {e}")
        return _basic_task_breakdown(project_description)


def _basic_task_breakdown(description: str) -> List[Dict]:
    """Fallback basic task breakdown."""
    return [
        {
            "title": "Project Setup and Planning",
            "description": "Set up project structure, define requirements, and create initial plan",
            "priority": "high",
            "estimated_hours": 8.0,
            "required_skills": ["Planning", "Documentation"]
        },
        {
            "title": "Core Development",
            "description": "Implement main features and functionality",
            "priority": "high",
            "estimated_hours": 40.0,
            "required_skills": ["Programming", "Problem Solving"]
        },
        {
            "title": "Testing and Quality Assurance",
            "description": "Write and execute tests, fix bugs",
            "priority": "medium",
            "estimated_hours": 16.0,
            "required_skills": ["Testing", "Debugging"]
        },
        {
            "title": "Documentation",
            "description": "Write user and technical documentation",
            "priority": "medium",
            "estimated_hours": 8.0,
            "required_skills": ["Documentation", "Writing"]
        },
        {
            "title": "Final Review and Deployment",
            "description": "Final review, polish, and deployment preparation",
            "priority": "high",
            "estimated_hours": 8.0,
            "required_skills": ["Review", "Deployment"]
        }
    ]

