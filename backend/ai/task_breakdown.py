import os
from typing import List, Dict
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


async def break_down_project(project_description: str, deadline: str) -> List[Dict]:
    """
    Break down a project into individual tasks using AI.
    Analyzes the project description and creates tasks based on the requirements and features mentioned.
    
    Args:
        project_description: The full project description to analyze
        deadline: Project deadline for task scheduling context
    
    Returns:
        List of task dictionaries with title, description, priority, estimated_hours, and required_skills
    """
    if not project_description or not project_description.strip():
        print("[AI Breakdown] Warning: Empty project description provided")
        return _basic_task_breakdown("Project requirements")
    
    if not OPENAI_API_KEY:
        print("[AI Breakdown] OpenAI API key not found, using basic breakdown")
        return _basic_task_breakdown(project_description)

    try:
        prompt = f"""
        Analyze the following project description carefully and break it down into specific, actionable tasks.
        
        Read and understand the project description thoroughly. Based on the requirements, features, and goals mentioned in the description, create tasks that directly address what needs to be accomplished.
        
        Each task should have:
        - title: Clear, specific task name that relates to the project description
        - description: Detailed description of what needs to be done, referencing specific aspects from the project description
        - priority: low, medium, high, or urgent (based on project requirements)
        - estimated_hours: Estimated hours to complete (realistic estimate)
        - required_skills: List of specific skills needed (e.g., ["Python", "SQL", "API Design", "React", "Database Design"])
        
        Project Description:
        {project_description}
        
        Deadline: {deadline}
        
        Instructions:
        1. Carefully read the entire project description
        2. Identify all major components, features, and requirements mentioned
        3. Create tasks that directly implement or address each component
        4. Ensure tasks are specific, actionable, and directly related to the project description
        5. Consider dependencies between tasks (order them logically)
        6. Include tasks for setup, core features, testing, documentation, and deployment as appropriate
        
        Return a JSON array of task objects. Create 5-10 tasks that comprehensively cover all aspects mentioned in the project description.
        Make sure each task is directly derived from and relevant to the project description provided.
        """
        
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=OPENAI_API_KEY)
        response = await client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an expert project management assistant. Your job is to carefully analyze project descriptions and break them down into specific, actionable tasks that directly address the requirements mentioned. Always base your task breakdown on the actual project description provided. Return only valid JSON array format."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=2000
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
    """Fallback basic task breakdown based on project description."""
    # Try to extract key information from description
    description_lower = description.lower()
    
    # Detect project type from description
    tasks = []
    
    # Always include setup
    tasks.append({
        "title": "Project Setup and Planning",
        "description": f"Set up project structure and plan implementation based on: {description[:100]}...",
        "priority": "high",
        "estimated_hours": 8.0,
        "required_skills": ["Planning", "Project Management"]
    })
    
    # Add core development task with description context
    core_desc = "Implement main features and functionality as described in the project requirements"
    if len(description) > 50:
        core_desc = f"Implement core features: {description[:150]}..."
    
    tasks.append({
        "title": "Core Development",
        "description": core_desc,
        "priority": "high",
        "estimated_hours": 40.0,
        "required_skills": ["Programming", "Development"]
    })
    
    # Add testing
    tasks.append({
        "title": "Testing and Quality Assurance",
        "description": "Write and execute tests to ensure all features work as specified in the project description",
        "priority": "medium",
        "estimated_hours": 16.0,
        "required_skills": ["Testing", "Quality Assurance"]
    })
    
    # Add documentation
    tasks.append({
        "title": "Documentation",
        "description": "Create documentation explaining the project features and implementation",
        "priority": "medium",
        "estimated_hours": 8.0,
        "required_skills": ["Documentation", "Technical Writing"]
    })
    
    # Add deployment
    tasks.append({
        "title": "Final Review and Deployment",
        "description": "Review project against requirements and prepare for deployment",
        "priority": "high",
        "estimated_hours": 8.0,
        "required_skills": ["Deployment", "Review"]
    })
    
    return tasks

