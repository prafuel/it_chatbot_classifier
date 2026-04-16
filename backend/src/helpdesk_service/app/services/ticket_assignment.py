"""
Ticket Assignment Engine.

Implements fair, load-balanced ticket assignment:
- Finds the least-loaded available IT_AGENT.
- If available → assigns ticket, status = IN_PROGRESS.
- If none available → status = PENDING.

Also provides reassignment logic for when an agent becomes available.
"""

import uuid
import logging
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.common.models import Ticket, User, StatusEnum, RoleEnum
from app.crud import crud_ticket

logger = logging.getLogger(__name__)


def _find_least_loaded_agent(db: Session) -> Optional[User]:
    """
    Find the available IT_AGENT with the fewest IN_PROGRESS tickets.
    Returns None if no agents are available.
    """
    # Subquery: count of in-progress tickets per agent
    in_progress_count = (
        db.query(
            Ticket.assigned_to,
            func.count(Ticket.ticket_id).label("active_tickets"),
        )
        .filter(Ticket.status == StatusEnum.IN_PROGRESS)
        .group_by(Ticket.assigned_to)
        .subquery()
    )

    # Join with users, filter available IT_AGENTs, order by least tickets
    agent = (
        db.query(User)
        .outerjoin(in_progress_count, User.user_id == in_progress_count.c.assigned_to)
        .filter(User.role == RoleEnum.IT_AGENT)
        .filter(User.is_available == True)
        .order_by(func.coalesce(in_progress_count.c.active_tickets, 0).asc())
        .first()
    )
    return agent


def auto_assign_ticket(db: Session, ticket_id: uuid.UUID) -> Ticket:
    """
    Automatically assign a ticket to the least-loaded available agent.
    If no agent is available, set status to PENDING.
    """
    ticket = crud_ticket.get_ticket(db, ticket_id)
    if not ticket:
        raise ValueError(f"Ticket {ticket_id} not found")

    agent = _find_least_loaded_agent(db)

    if agent:
        ticket = crud_ticket.assign_ticket(db, ticket_id, agent.user_id)
        logger.info(
            f"Auto-assigned ticket {ticket_id} to agent {agent.user_id} ({agent.name})"
        )
    else:
        ticket = crud_ticket.update_ticket_status(db, ticket_id, StatusEnum.PENDING)
        logger.info(f"No available agents — ticket {ticket_id} set to PENDING")

    return ticket


def reassign_pending_tickets(db: Session) -> list:
    """
    Called when an agent becomes available.
    Picks the oldest PENDING tickets and assigns them to available agents.
    Returns list of reassigned tickets.
    """
    reassigned = []

    # Get all pending tickets ordered by creation time (oldest first)
    pending_tickets = (
        db.query(Ticket)
        .filter(Ticket.status == StatusEnum.PENDING)
        .order_by(Ticket.created_at.asc())
        .all()
    )

    for ticket in pending_tickets:
        agent = _find_least_loaded_agent(db)
        if not agent:
            logger.info("No more available agents — stopping reassignment")
            break

        crud_ticket.assign_ticket(db, ticket.ticket_id, agent.user_id)
        reassigned.append(ticket)
        logger.info(
            f"Reassigned pending ticket {ticket.ticket_id} to agent {agent.user_id}"
        )

    return reassigned
