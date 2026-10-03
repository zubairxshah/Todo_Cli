from sqlmodel import Session, select
from typing import List, Optional
from ..models.skill import Skill, SkillCreate, SkillUpdate
import uuid


def create_skill(session: Session, skill_data: SkillCreate, user_id: uuid.UUID) -> Skill:
    """Create a new skill for a user"""
    db_skill = Skill(
        name=skill_data.name,
        description=skill_data.description,
        category=skill_data.category,
        proficiency_level=skill_data.proficiency_level,
        user_id=user_id
    )
    session.add(db_skill)
    session.commit()
    session.refresh(db_skill)
    return db_skill


def get_skills_by_user(session: Session, user_id: uuid.UUID) -> List[Skill]:
    """Get all skills for a specific user"""
    skills = session.exec(
        select(Skill).where(Skill.user_id == user_id)
    ).all()
    return skills


def get_skill_by_id(session: Session, skill_id: uuid.UUID, user_id: uuid.UUID) -> Optional[Skill]:
    """Get a specific skill by ID for a user"""
    skill = session.get(Skill, skill_id)
    if skill and skill.user_id == user_id:
        return skill
    return None


def update_skill(session: Session, skill_id: uuid.UUID, user_id: uuid.UUID, skill_update: SkillUpdate) -> Optional[Skill]:
    """Update a specific skill for a user"""
    db_skill = session.get(Skill, skill_id)
    if not db_skill or db_skill.user_id != user_id:
        return None

    # Update the skill fields
    for field, value in skill_update.dict(exclude_unset=True).items():
        setattr(db_skill, field, value)

    # Update the updated_at timestamp
    from datetime import datetime, timezone
    db_skill.updated_at = datetime.now(timezone.utc)

    session.add(db_skill)
    session.commit()
    session.refresh(db_skill)
    return db_skill


def delete_skill(session: Session, skill_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    """Delete a specific skill for a user"""
    db_skill = session.get(Skill, skill_id)
    if not db_skill or db_skill.user_id != user_id:
        return False

    session.delete(db_skill)
    session.commit()
    return True