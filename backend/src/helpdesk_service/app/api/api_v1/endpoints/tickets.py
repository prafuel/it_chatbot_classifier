"""
Ticket API endpoints.
"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.common.database import get_db
from app.common.models import StatusEnum, PriorityEnum, SourceEnum
from app.crud import crud_ticket
from app.services import ticket_assignment
from app import schema

router = APIRouter(prefix="/tickets", tags=["Tickets"])


@router.post("/", response_model=schema.TicketResponse, status_code=status.HTTP_201_CREATED)
def create_ticket(payload: schema.TicketCreate, db: Session = Depends(get_db)):
    """Create a new ticket and auto-assign to an available agent."""
    ticket = crud_ticket.create_ticket(
        db=db,
        title=payload.title,
        description=payload.description,
        created_by=payload.created_by,
        priority=payload.priority,
        category_id=payload.category_id,
        sub_category_id=payload.sub_category_id,
        source=payload.source,
    )
    # Attempt automatic assignment
    ticket = ticket_assignment.auto_assign_ticket(db, ticket.ticket_id)
    return ticket


@router.get("/", response_model=list[schema.TicketResponse])
def list_tickets(
    status_filter: Optional[StatusEnum] = Query(None, alias="status"),
    assigned_to: Optional[uuid.UUID] = None,
    created_by: Optional[uuid.UUID] = None,
    priority: Optional[PriorityEnum] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """List tickets with optional filters."""
    return crud_ticket.list_tickets(
        db, status=status_filter, assigned_to=assigned_to,
        created_by=created_by, priority=priority, skip=skip, limit=limit,
    )


@router.get("/{ticket_id}", response_model=schema.TicketResponse)
def get_ticket(ticket_id: uuid.UUID, db: Session = Depends(get_db)):
    """Get a single ticket by ID."""
    ticket = crud_ticket.get_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket


@router.patch("/{ticket_id}/status", response_model=schema.TicketResponse)
def update_ticket_status(
    ticket_id: uuid.UUID,
    payload: schema.TicketStatusUpdate,
    db: Session = Depends(get_db),
):
    """Update ticket status. When resolving, triggers reassignment of pending tickets."""
    ticket = crud_ticket.update_ticket_status(db, ticket_id, payload.status)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    # When a ticket is resolved, try to reassign pending tickets
    if payload.status == StatusEnum.RESOLVED:
        ticket_assignment.reassign_pending_tickets(db)

    return ticket


@router.patch("/{ticket_id}/assign", response_model=schema.TicketResponse)
def assign_ticket(
    ticket_id: uuid.UUID,
    payload: schema.TicketAssign,
    db: Session = Depends(get_db),
):
    """Manually assign a ticket to an IT agent."""
    ticket = crud_ticket.assign_ticket(db, ticket_id, payload.assigned_to)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket


@router.patch("/{ticket_id}/auto-assign", response_model=schema.TicketResponse)
def auto_assign_ticket(
    ticket_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """Automatically assign a ticket to the least-loaded available agent."""
    ticket = ticket_assignment.auto_assign_ticket(db, ticket_id)
    return ticket


@router.patch("/{ticket_id}", response_model=schema.TicketResponse)
def update_ticket(
    ticket_id: uuid.UUID,
    payload: schema.TicketUpdate,
    db: Session = Depends(get_db),
):
    """Partial update of ticket fields (title, description, priority, category)."""
    ticket = crud_ticket.update_ticket(
        db, ticket_id,
        title=payload.title,
        description=payload.description,
        priority=payload.priority,
        category_id=payload.category_id,
        sub_category_id=payload.sub_category_id,
    )
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket
