"""
Dashboard & Analytics API endpoints.

Role-based filtering:
- ADMIN: sees overall stats across all tickets/agents.
- IT_AGENT: sees only their own assigned ticket stats.
"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.common.database import get_db
from app.common.models import Ticket, User, StatusEnum, RoleEnum
from app.crud import crud_ticket
from app.api.deps import get_current_user_optional

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/ticket-summary")
def ticket_summary(
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    """
    Get ticket counts grouped by status.
    IT_AGENTs see only tickets assigned to them.
    ADMINs (and unauthenticated callers) see overall counts.
    """
    query = db.query(Ticket.status, func.count(Ticket.ticket_id))

    if current_user and current_user.role == RoleEnum.IT_AGENT:
        query = query.filter(Ticket.assigned_to == current_user.user_id)

    rows = query.group_by(Ticket.status).all()
    return {status.value: count for status, count in rows}


@router.get("/agent-stats")
def agent_stats(
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    """
    Get number of resolved tickets per IT agent.
    IT_AGENTs see only their own stats.
    """
    query = (
        db.query(Ticket.assigned_to, func.count(Ticket.ticket_id))
        .filter(Ticket.status == StatusEnum.RESOLVED)
    )

    if current_user and current_user.role == RoleEnum.IT_AGENT:
        query = query.filter(Ticket.assigned_to == current_user.user_id)

    rows = query.group_by(Ticket.assigned_to).all()
    return [
        {"agent_id": str(agent_id), "resolved_count": count}
        for agent_id, count in rows
        if agent_id
    ]


@router.get("/frequent-issues")
def frequent_issues(
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """Get most frequently raised issue categories."""
    return crud_ticket.frequent_categories(db, limit=limit)
