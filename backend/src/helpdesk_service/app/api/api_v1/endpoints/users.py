"""
User-related endpoints for the Helpdesk Service.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from app.common.database import get_db
from app.common.models import User, RoleEnum
from app.common.auth import get_it_staff_user
from app import schema

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/it-agents", response_model=List[schema.UserResponse])
def list_it_agents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_it_staff_user),
):
    """List all users with IT_AGENT role. (IT Staff Only)"""
    agents = db.query(User).filter(User.role == RoleEnum.IT_AGENT).all()
    
    # Map to schema response
    return [
        schema.UserResponse(
            user_id=agent.id,
            name=f"{agent.first_name} {agent.last_name}",
            email=agent.email,
            role=agent.role,
            is_available=agent.is_available,
            created_at=agent.created_at
        )
        for agent in agents
    ]
