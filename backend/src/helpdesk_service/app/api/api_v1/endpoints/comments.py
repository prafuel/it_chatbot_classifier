"""
Ticket Comments API endpoints.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.common.database import get_db
from app.common.models import RoleEnum, User
from app.common.auth import get_current_user
from app.crud import crud_comment, crud_ticket
from app import schema

router = APIRouter(prefix="/tickets/{ticket_id}/comments", tags=["Comments"])


@router.post("/", response_model=schema.TicketCommentResponse, status_code=status.HTTP_201_CREATED)
def add_comment(
    ticket_id: uuid.UUID,
    payload: schema.TicketCommentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add a comment to a ticket. Users can only comment on their own tickets."""
    ticket = crud_ticket.get_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    if current_user.role == RoleEnum.USER and ticket.created_by != current_user.user_id:
        raise HTTPException(status_code=403, detail="Not authorized to comment on this ticket")

    return crud_comment.add_comment(db, ticket_id, current_user.user_id, payload.comment_text)


@router.get("/", response_model=list[schema.TicketCommentResponse])
def list_comments(
    ticket_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all comments for a ticket. Users can only view their own tickets."""
    ticket = crud_ticket.get_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
        
    if current_user.role == RoleEnum.USER and ticket.created_by != current_user.user_id:
        raise HTTPException(status_code=403, detail="Not authorized to view comments for this ticket")

    return crud_comment.list_comments_for_ticket(db, ticket_id)
