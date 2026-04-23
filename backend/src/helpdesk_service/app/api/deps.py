"""
Authentication dependencies for role-based access control.
"""

import uuid
from typing import Optional

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.common.auth import JWTBearer
from app.common.database import get_db
from app.common.models import User, RoleEnum


async def get_current_user(
    token_payload: dict = Depends(JWTBearer()),
    db: Session = Depends(get_db),
) -> User:
    """Extract the current user from the JWT token."""
    user_id = token_payload.get("id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing user id",
        )
    user = db.query(User).filter(User.user_id == uuid.UUID(user_id)).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return user


async def get_current_user_optional(
    token_payload: dict = Depends(JWTBearer(auto_error=False)),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """Optionally extract the current user (returns None if no token)."""
    if not token_payload:
        return None
    user_id = token_payload.get("id")
    if not user_id:
        return None
    return db.query(User).filter(User.user_id == uuid.UUID(user_id)).first()


async def get_admin_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Require the current user to be an ADMIN."""
    if current_user.role != RoleEnum.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user
