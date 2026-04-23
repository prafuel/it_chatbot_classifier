"""
Ticket Comments API endpoints.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.common.database import get_db
from app.common.models import User
from app.crud import crud_comment, crud_ticket
from app import schema
from app.api.deps import get_current_user_optional


router = APIRouter(prefix="/tickets/{ticket_id}/comments", tags=["Comments"])


class CommentCreateRequest(BaseModel):
    """Frontend sends only comment_text; user_id comes from the token."""
    comment_text: str


@router.post("/", response_model=schema.TicketCommentResponse, status_code=status.HTTP_201_CREATED)
def add_comment(
    ticket_id: uuid.UUID,
    payload: CommentCreateRequest,
    current_user: User = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    """Add a comment to a ticket. user_id is extracted from the JWT token."""
    ticket = crud_ticket.get_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    # Use authenticated user if available, otherwise require user_id
    user_id = current_user.user_id if current_user else None
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required to add comments",
        )

    return crud_comment.add_comment(db, ticket_id, user_id, payload.comment_text)


@router.get("/", response_model=list[schema.TicketCommentResponse])
def list_comments(ticket_id: uuid.UUID, db: Session = Depends(get_db)):
    """List all comments for a ticket."""
    return crud_comment.list_comments_for_ticket(db, ticket_id)
