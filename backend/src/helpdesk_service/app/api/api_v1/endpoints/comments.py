"""
Ticket Comments API endpoints.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.common.database import get_db
from app.crud import crud_comment, crud_ticket
from app import schema

router = APIRouter(prefix="/tickets/{ticket_id}/comments", tags=["Comments"])


@router.post("/", response_model=schema.TicketCommentResponse, status_code=status.HTTP_201_CREATED)
def add_comment(
    ticket_id: uuid.UUID,
    payload: schema.TicketCommentCreate,
    db: Session = Depends(get_db),
):
    """Add a comment to a ticket."""
    ticket = crud_ticket.get_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return crud_comment.add_comment(db, ticket_id, payload.user_id, payload.comment_text)


@router.get("/", response_model=list[schema.TicketCommentResponse])
def list_comments(ticket_id: uuid.UUID, db: Session = Depends(get_db)):
    """List all comments for a ticket."""
    return crud_comment.list_comments_for_ticket(db, ticket_id)
