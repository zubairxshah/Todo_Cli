from sqlmodel import SQLModel, Field
from typing import Optional
import uuid
from datetime import datetime, timezone
from pydantic import BaseModel


class SkillBase(SQLModel):
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    proficiency_level: Optional[int] = Field(default=1, ge=1, le=5)  # 1-5 scale


class SkillCreate(SkillBase):
    pass


class Skill(SkillBase, table=True):
    id: Optional[uuid.UUID] = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), nullable=False)


class SkillRead(SQLModel):
    id: uuid.UUID
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    proficiency_level: Optional[int] = 1  # 1-5 scale
    user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class SkillUpdate(SQLModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    proficiency_level: Optional[int] = Field(default=None, ge=1, le=5)  # 1-5 scale