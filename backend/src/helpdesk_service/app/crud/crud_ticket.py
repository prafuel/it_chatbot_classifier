"""
CRUD operations for Tickets.
"""

import uuid
import logging
from datetime import datetime
from typing import Optional, List

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.common.models import Ticket, StatusEnum, PriorityEnum, SourceEnum

logger = logging.getLogger(__name__)


def create_ticket(
    db: Session,
    title: str,
    description: str,
    created_by: uuid.UUID,
    priority: PriorityEnum = PriorityEnum.MEDIUM,
    category_id: Optional[uuid.UUID] = None,
    sub_category_id: Optional[uuid.UUID] = None,
    source: SourceEnum = SourceEnum.chatbot,
) -> Ticket:
    """Create a new ticket with NOT_ASSIGNED status."""
    ticket = Ticket(
        title=title,
        description=description,
        created_by=created_by,
        priority=priority,
        category_id=category_id,
        sub_category_id=sub_category_id,
        source=source,
        status=StatusEnum.NOT_ASSIGNED,
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    logger.info(f"Ticket created: {ticket.ticket_id}")
    return ticket


def get_ticket(db: Session, ticket_id: uuid.UUID) -> Optional[Ticket]:
    """Fetch a single ticket by ID."""
    return db.query(Ticket).filter(Ticket.ticket_id == ticket_id).first()


def list_tickets(
    db: Session,
    status: Optional[StatusEnum] = None,
    assigned_to: Optional[uuid.UUID] = None,
    created_by: Optional[uuid.UUID] = None,
    priority: Optional[PriorityEnum] = None,
    skip: int = 0,
    limit: int = 50,
) -> List[Ticket]:
    """List tickets with optional filters and pagination."""
    query = db.query(Ticket)
    if status:
        query = query.filter(Ticket.status == status)
    if assigned_to:
        query = query.filter(Ticket.assigned_to == assigned_to)
    if created_by:
        query = query.filter(Ticket.created_by == created_by)
    if priority:
        query = query.filter(Ticket.priority == priority)
    return query.order_by(Ticket.created_at.desc()).offset(skip).limit(limit).all()


def update_ticket_status(
    db: Session, ticket_id: uuid.UUID, new_status: StatusEnum
) -> Optional[Ticket]:
    """Transition a ticket's status. Sets resolved_at when RESOLVED."""
    ticket = get_ticket(db, ticket_id)
    if not ticket:
        return None
    ticket.status = new_status
    ticket.updated_at = datetime.utcnow()
    if new_status == StatusEnum.RESOLVED:
        ticket.resolved_at = datetime.utcnow()
    db.commit()
    db.refresh(ticket)
    logger.info(f"Ticket {ticket_id} status -> {new_status.value}")
    return ticket


def assign_ticket(
    db: Session, ticket_id: uuid.UUID, agent_id: uuid.UUID
) -> Optional[Ticket]:
    """Assign a ticket to an IT agent and set status to IN_PROGRESS."""
    ticket = get_ticket(db, ticket_id)
    if not ticket:
        return None
    ticket.assigned_to = agent_id
    ticket.status = StatusEnum.IN_PROGRESS
    ticket.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(ticket)
    logger.info(f"Ticket {ticket_id} assigned to agent {agent_id}")
    return ticket


def update_ticket(
    db: Session,
    ticket_id: uuid.UUID,
    title: Optional[str] = None,
    description: Optional[str] = None,
    priority: Optional[PriorityEnum] = None,
    category_id: Optional[uuid.UUID] = None,
    sub_category_id: Optional[uuid.UUID] = None,
) -> Optional[Ticket]:
    """Partial update of ticket fields."""
    ticket = get_ticket(db, ticket_id)
    if not ticket:
        return None
    if title is not None:
        ticket.title = title
    if description is not None:
        ticket.description = description
    if priority is not None:
        ticket.priority = priority
    if category_id is not None:
        ticket.category_id = category_id
    if sub_category_id is not None:
        ticket.sub_category_id = sub_category_id
    ticket.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(ticket)
    return ticket


def count_tickets_by_status(db: Session) -> dict:
    """Return ticket counts grouped by status."""
    rows = (
        db.query(Ticket.status, func.count(Ticket.ticket_id))
        .group_by(Ticket.status)
        .all()
    )
    return {status.value: count for status, count in rows}


def count_resolved_by_agent(db: Session) -> List[dict]:
    """Return number of resolved tickets per agent."""
    rows = (
        db.query(Ticket.assigned_to, func.count(Ticket.ticket_id))
        .filter(Ticket.status == StatusEnum.RESOLVED)
        .group_by(Ticket.assigned_to)
        .all()
    )
    return [{"agent_id": str(agent_id), "resolved_count": count} for agent_id, count in rows if agent_id]


def frequent_categories(db: Session, limit: int = 10) -> List[dict]:
    """Return most frequently used categories across tickets."""
    rows = (
        db.query(Ticket.category_id, func.count(Ticket.ticket_id).label("ticket_count"))
        .filter(Ticket.category_id.isnot(None))
        .group_by(Ticket.category_id)
        .order_by(func.count(Ticket.ticket_id).desc())
        .limit(limit)
        .all()
    )
    return [{"category_id": str(cat_id), "ticket_count": count} for cat_id, count in rows]
