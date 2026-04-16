"""
CRUD operations for Ticket Comments.
"""

import uuid
import logging
from typing import List

from sqlalchemy.orm import Session

from app.common.models import TicketComment

logger = logging.getLogger(__name__)


def add_comment(
    db: Session,
    ticket_id: uuid.UUID,
    user_id: uuid.UUID,
    comment_text: str,
) -> TicketComment:
    comment = TicketComment(
        ticket_id=ticket_id,
        user_id=user_id,
        comment_text=comment_text,
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    logger.info(f"Comment added to ticket {ticket_id} by user {user_id}")
    return comment


def list_comments_for_ticket(
    db: Session, ticket_id: uuid.UUID
) -> List[TicketComment]:
    return (
        db.query(TicketComment)
        .filter(TicketComment.ticket_id == ticket_id)
        .order_by(TicketComment.created_at.asc())
        .all()
    )
