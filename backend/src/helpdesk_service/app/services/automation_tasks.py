import asyncio
import logging
from sqlalchemy.orm import Session
from app.common.models import Ticket, StatusEnum, ApprovalStatusEnum
from app.crud import crud_ticket
from app.services import ticket_assignment
from app.common.database import SessionLocal

logger = logging.getLogger(__name__)

async def auto_approve_ticket_task(ticket_id: str):
    """
    Background task that waits for 60 seconds and then auto-approves the ticket.
    """
    logger.info(f"Scheduled auto-approval for ticket {ticket_id} in 60s")
    await asyncio.sleep(60)
    
    db: Session = SessionLocal()
    try:
        ticket = db.query(Ticket).filter(Ticket.ticket_id == ticket_id).first()
        if ticket and ticket.approval_status == ApprovalStatusEnum.PENDING:
            ticket.approval_status = ApprovalStatusEnum.APPROVED
            logger.info(f"Auto-approved ticket {ticket_id}")
            
            # If ticket was waiting for approval, it can now move to IN_PROGRESS if an agent is assigned
            # or auto-assign again if it was pending
            if ticket.assigned_to:
                ticket.status = StatusEnum.IN_PROGRESS
            else:
                ticket_assignment.auto_assign_ticket(db, ticket.ticket_id)
            
            db.commit()
            logger.info(f"Ticket {ticket_id} moved to next stage after auto-approval")
    except Exception as e:
        logger.error(f"Error in auto-approval task for ticket {ticket_id}: {e}")
        db.rollback()
    finally:
        db.close()
