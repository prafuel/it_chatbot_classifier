"""
Users endpoints — list IT agents, etc.
"""
from typing import List
import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.common.database import get_db
from app.common.models import User, RoleEnum

router = APIRouter(prefix="/users", tags=["users"])


class AgentResponse(BaseModel):
    user_id: uuid.UUID
    name: str
    email: str
    is_available: bool
    role: str

    class Config:
        from_attributes = True


@router.get(
    "/it-agents",
    response_model=List[AgentResponse],
    summary="List all IT agents",
)
def list_it_agents(db: Session = Depends(get_db)):
    """Return all users with role IT_AGENT."""
    agents = (
        db.query(User)
        .filter(User.role == RoleEnum.IT_AGENT)
        .order_by(User.name)
        .all()
    )
    return agents
