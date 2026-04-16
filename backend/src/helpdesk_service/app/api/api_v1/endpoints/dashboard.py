"""
Dashboard & Analytics API endpoints.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.common.database import get_db
from app.crud import crud_ticket

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/ticket-summary")
def ticket_summary(db: Session = Depends(get_db)):
    """Get ticket counts grouped by status."""
    return crud_ticket.count_tickets_by_status(db)


@router.get("/agent-stats")
def agent_stats(db: Session = Depends(get_db)):
    """Get number of resolved tickets per IT agent."""
    return crud_ticket.count_resolved_by_agent(db)


@router.get("/frequent-issues")
def frequent_issues(
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """Get most frequently raised issue categories."""
    return crud_ticket.frequent_categories(db, limit=limit)
