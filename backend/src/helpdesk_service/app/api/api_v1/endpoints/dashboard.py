"""
Dashboard & Analytics API endpoints.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.common.database import get_db
from app.common.models import User, RoleEnum
from app.common.auth import get_it_staff_user
from app.crud import crud_ticket

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/ticket-summary")
def ticket_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_it_staff_user),
):
    """Get ticket counts grouped by status. (IT Staff Only)"""
    agent_id = current_user.id if current_user.role == RoleEnum.IT_AGENT else None
    return crud_ticket.count_tickets_by_status(db, agent_id=agent_id)


@router.get("/agent-stats")
def agent_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_it_staff_user),
):
    """Get number of resolved tickets per IT agent. (IT Staff Only)"""
    agent_id = current_user.id if current_user.role == RoleEnum.IT_AGENT else None
    return crud_ticket.count_resolved_by_agent(db, agent_id=agent_id)


@router.get("/frequent-issues")
def frequent_issues(
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_it_staff_user),
):
    """Get most frequently raised issue categories. (IT Staff Only)"""
    agent_id = current_user.id if current_user.role == RoleEnum.IT_AGENT else None
    return crud_ticket.frequent_categories(db, limit=limit, agent_id=agent_id)
