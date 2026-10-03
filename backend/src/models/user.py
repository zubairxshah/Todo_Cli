from sqlmodel import SQLModel, Field
from typing import Optional
import uuid
from datetime import datetime, timezone
from pydantic import BaseModel
import bcrypt


class UserBase(SQLModel):
    email: str = Field(unique=True, index=True)
    is_active: bool = True


class UserCreate(UserBase):
    password: str  # Will be hashed before storing


class User(UserBase, table=True):
    id: Optional[uuid.UUID] = Field(default_factory=uuid.uuid4, primary_key=True)
    hashed_password: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), nullable=False)


class UserRead(SQLModel):
    id: uuid.UUID
    email: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class UserLogin(BaseModel):
    email: str
    password: str


def hash_password(password: str) -> str:
    """Hash a plain text password."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain text password against its hash."""
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))