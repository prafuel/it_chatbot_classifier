import uuid
import logging
from typing import Optional
from sqlalchemy.orm import Session
from app.common.models import User, RoleEnum

logger = logging.getLogger(__name__)

def get_designated_approver(db: Session, approver_type: str) -> Optional[User]:
    """
    Find a user matching the approver type.
    For now, maps types to specific roles or searching by name/email patterns.
    """
    if approver_type == "Finance Head":
        # Search for a user with 'finance' in name/email or a specific role if added
        return db.query(User).filter(User.name.ilike("%finance%")).first()
    elif approver_type == "BU Head" or approver_type == "Manager":
        # Fallback to an ADMIN user if specific head not found
        return db.query(User).filter(User.role == RoleEnum.ADMIN).first()
    
    return None

def determine_approver_id(db: Session, approver_type: str) -> Optional[uuid.UUID]:
    approver = get_designated_approver(db, approver_type)
    return approver.user_id if approver else None
