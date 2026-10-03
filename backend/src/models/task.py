from sqlmodel import SQLModel, Field
from typing import Optional
import re
import uuid
from datetime import date, datetime, timezone
from pydantic import field_validator

_TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


def _check_due_time(value: Optional[str]) -> Optional[str]:
    """Due time is a local wall-clock time "HH:MM"; empty means no time."""
    if value is None or value == "":
        return None
    if not _TIME_RE.match(value):
        raise ValueError("due_time must be HH:MM (24-hour)")
    return value


class TaskBase(SQLModel):
    title: str
    description: Optional[str] = None
    completed: bool = False
    # Date-only plus optional local time: avoids timezone conversion, the
    # browser interprets both in the user's own timezone
    due_date: Optional[date] = None
    due_time: Optional[str] = Field(default=None, max_length=5)

    @field_validator("due_time")
    @classmethod
    def validate_due_time(cls, value):
        return _check_due_time(value)


class TaskCreate(TaskBase):
    pass


class Task(TaskBase, table=True):
    id: Optional[uuid.UUID] = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), nullable=False)


class TaskRead(SQLModel):
    id: uuid.UUID
    title: str
    description: Optional[str] = None
    completed: bool = False
    due_date: Optional[date] = None
    due_time: Optional[str] = None
    user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class TaskUpdate(SQLModel):
    title: Optional[str] = None
    description: Optional[str] = None
    completed: Optional[bool] = None
    due_date: Optional[date] = None
    due_time: Optional[str] = None

    @field_validator("due_time")
    @classmethod
    def validate_due_time(cls, value):
        return _check_due_time(value)
