from sqlmodel import create_engine, Session, SQLModel
from typing import Generator
import os
from contextlib import contextmanager
from pathlib import Path

# Load environment variables from .env file - look in parent directories
try:
    from dotenv import load_dotenv
    # Try to find .env.local first, then .env in current dir, then parent dirs
    env_path = Path(__file__).parent.parent.parent / ".env.local"
    if not env_path.exists():
        env_path = Path(__file__).parent.parent.parent / ".env"
    if not env_path.exists():
        env_path = Path(".env.local")
    if not env_path.exists():
        env_path = Path(".env")
    load_dotenv(dotenv_path=env_path, override=False)
    if env_path.exists():
        print(f"Loaded environment from: {env_path}")
except ImportError:
    pass  # dotenv not available, that's fine

# Import models to register them with SQLModel
try:
    # Try relative imports first
    from .models.task import Task
    from .models.skill import Skill
    from .models.user import User
except ImportError:
    # Fall back to absolute imports
    import sys
    sys.path.insert(0, os.path.dirname(__file__))
    from models.task import Task
    from models.skill import Skill
    from models.user import User

# Get database URL from environment, with a default for development
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./todo_test.db")

# For PostgreSQL URLs, ensure proper driver is specified
if DATABASE_URL.startswith("postgres://"):
    # Convert postgres:// to postgresql:// for SQLAlchemy 2.0 compatibility
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg2://", 1)
    print(f"Converted PostgreSQL URL for SQLAlchemy compatibility")

print(f"Using DATABASE_URL: {DATABASE_URL[:50]}...")

# Create the engine with proper configuration
is_sqlite = "sqlite" in DATABASE_URL
engine = create_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False} if is_sqlite else {},
    # Hosted Postgres (e.g. Neon) closes idle connections; test before reuse
    pool_pre_ping=not is_sqlite,
    pool_recycle=300 if not is_sqlite else -1,
)


# Create tables function
def create_db_and_tables():
    """Create all database tables"""
    SQLModel.metadata.create_all(engine, checkfirst=True)
    _add_missing_task_columns()


def _add_missing_task_columns():
    """create_all() never alters existing tables, so add columns introduced
    after a database was first created (works on SQLite and PostgreSQL)."""
    from sqlalchemy import inspect, text

    new_columns = {"due_date": "DATE", "due_time": "VARCHAR(5)"}
    existing = {col["name"] for col in inspect(engine).get_columns("task")}
    with engine.begin() as conn:
        for name, sql_type in new_columns.items():
            if name not in existing:
                conn.execute(text(f"ALTER TABLE task ADD COLUMN {name} {sql_type}"))
                print(f"Added column task.{name}")


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session