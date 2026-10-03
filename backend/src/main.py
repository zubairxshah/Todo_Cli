from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from sqlmodel import Session, select
from typing import List
import uuid
from datetime import datetime, timezone

try:
    # Try relative imports first (when running as package)
    from .database import get_session, create_db_and_tables
    from .models.task import Task, TaskRead, TaskCreate, TaskUpdate
    from .auth.jwt_handler import get_current_user
    from .api.auth import router as auth_router
    from .api.skills import router as skills_router
    from .api.agents import router as agents_router
    from .api.chatbot.chat_controller import router as chat_router
    from .agents.agent_registry import AgentRegistry
    from .agents.config import AgentConfig
except ImportError:
    # Fall back to absolute imports (when running directly)
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__)))
    from database import get_session, create_db_and_tables
    from models.task import Task, TaskRead, TaskCreate, TaskUpdate
    from auth.jwt_handler import get_current_user
    from api.auth import router as auth_router
    from api.skills import router as skills_router
    from api.agents import router as agents_router
    from api.chatbot.chat_controller import router as chat_router
    from agents.agent_registry import AgentRegistry
    from agents.config import AgentConfig

app = FastAPI(title="Todo API", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins during development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(skills_router)
app.include_router(agents_router)
app.include_router(chat_router)




# Global agent registry instance
agent_registry = AgentRegistry()


@app.on_event("startup")
async def on_startup():
    create_db_and_tables()

    # OpenRouter is now optional - it will use simulated responses if not configured
    import os
    api_key = os.getenv("OPEN_ROUTER_API_KEY")
    base_url = os.getenv("OPEN_ROUTER_URL")

    if api_key and base_url:
        print("OpenRouter configured for chat functionality")
        if base_url != "https://openrouter.ai/api/v1":
            print(f"WARNING: OPEN_ROUTER_URL differs from expected. Got: {base_url}")
    else:
        print("OpenRouter not fully configured. Using simulated responses for chat.")

    # Initialize default agents
    try:
        # Register default agent types
        from .agents.agents import TaskAgent, PlanningAgent

        agent_registry.register_agent_type("task_agent", TaskAgent)
        agent_registry.register_agent_type("planning_agent", PlanningAgent)

        # Create default agent instances
        task_agent_config = AgentConfig(
            name="task_agent",
            description="Default task execution agent"
        )
        agent_registry.create_and_register(task_agent_config)

        planning_agent_config = AgentConfig(
            name="planning_agent",
            description="Default planning agent"
        )
        agent_registry.create_and_register(planning_agent_config)

        print("Agent registry initialized with default agents")
    except Exception as e:
        print(f"Warning: Could not initialize agent registry: {e}")


@app.get("/")
def read_root():
    return {"message": "Todo API - Phase 5 Implementation - Ready for Production"}


@app.get("/health")
def health_check():
    """Health check endpoint for Render deployment"""
    return {"status": "healthy", "message": "Todo API is running"}


@app.post("/api/tasks", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
def create_task(
    task: TaskCreate,
    user_id: str = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    # Create a new task with the authenticated user's ID
    db_task = Task(
        title=task.title,
        description=task.description,
        completed=task.completed,
        due_date=task.due_date,
        due_time=task.due_time,
        user_id=uuid.UUID(user_id) if isinstance(user_id, str) else user_id
    )
    session.add(db_task)
    session.commit()
    session.refresh(db_task)
    return db_task


@app.get("/api/tasks", response_model=List[TaskRead])
def read_tasks(
    user_id: str = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    # Get tasks for the authenticated user only
    user_uuid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
    # Same order the chatbot uses for "task 1", "task 2", ...
    tasks = session.exec(
        select(Task).where(Task.user_id == user_uuid).order_by(Task.created_at)
    ).all()
    return tasks


@app.get("/api/tasks/{task_id}", response_model=TaskRead)
def read_task(
    task_id: uuid.UUID,
    user_id: str = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    # Get a specific task for the authenticated user
    user_uuid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
    task = session.get(Task, task_id)

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.user_id != user_uuid:
        raise HTTPException(status_code=403, detail="Not authorized to access this task")

    return task


@app.put("/api/tasks/{task_id}", response_model=TaskRead)
def update_task(
    task_id: uuid.UUID,
    task_update: TaskUpdate,
    user_id: str = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    # Update a specific task for the authenticated user
    user_uuid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
    db_task = session.get(Task, task_id)

    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")

    if db_task.user_id != user_uuid:
        raise HTTPException(status_code=403, detail="Not authorized to access this task")

    # Update the task fields
    for field, value in task_update.dict(exclude_unset=True).items():
        setattr(db_task, field, value)

    # Update the updated_at timestamp
    db_task.updated_at = datetime.now(timezone.utc)

    session.add(db_task)
    session.commit()
    session.refresh(db_task)
    return db_task


@app.patch("/api/tasks/{task_id}/toggle", response_model=TaskRead)
def toggle_task_completion(
    task_id: uuid.UUID,
    user_id: str = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    # Toggle the completion status of a task
    user_uuid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
    db_task = session.get(Task, task_id)

    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")

    if db_task.user_id != user_uuid:
        raise HTTPException(status_code=403, detail="Not authorized to access this task")

    # Toggle the completion status
    db_task.completed = not db_task.completed
    # Update the updated_at timestamp
    db_task.updated_at = datetime.now(timezone.utc)
    session.add(db_task)
    session.commit()
    session.refresh(db_task)
    return db_task


@app.delete("/api/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
    task_id: uuid.UUID,
    user_id: str = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    # Delete a specific task for the authenticated user
    user_uuid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
    db_task = session.get(Task, task_id)

    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")

    if db_task.user_id != user_uuid:
        raise HTTPException(status_code=403, detail="Not authorized to access this task")

    session.delete(db_task)
    session.commit()
    return


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    # Serve the favicon file
    import os
    from pathlib import Path

    favicon_path = Path(__file__).parent / "static" / "favicon.ico"

    if favicon_path.exists():
        with open(favicon_path, "rb") as f:
            content = f.read()
        return Response(content=content, media_type="image/x-icon")
    else:
        # Return a minimal transparent favicon if the file doesn't exist
        # This is a minimal 16x16 transparent favicon in bytes
        transparent_favicon = (
            b'\x00\x00\x01\x00\x01\x00\x10\x10\x00\x00\x01\x00\x08\x00'
            b'\x00\x00\x00\x00@\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
            b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
            b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
            b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
            b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
            b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
            b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
            b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
            b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
            b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
            b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        )
        return Response(content=transparent_favicon, media_type="image/x-icon")


@app.get("/.well-known/appspecific/com.chrome.devtools.json", include_in_schema=False)
def chrome_devtools_manifest():
    # Return an empty JSON response to prevent 404 errors
    # This handles Chrome's attempt to find devtools configuration
    from fastapi.responses import JSONResponse
    return JSONResponse(content={}, status_code=200)