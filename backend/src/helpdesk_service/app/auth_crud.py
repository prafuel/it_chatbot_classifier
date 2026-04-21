"""
CRUD operations for User auth (migrated from usermanagementservice).
"""
from datetime import datetime

from sqlalchemy.orm import Session

from app.common.models import User
from app.auth_schema import SignUpRequest


class CRUDUser:
    def create_user(self, db: Session, user_data: SignUpRequest) -> User:
        new_user = User(
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            name=f"{user_data.first_name} {user_data.last_name}",
            email=user_data.email,
            encrypted_password=user_data.password,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return new_user

    def get_user_by_email(self, db: Session, email: str) -> User | None:
        return db.query(User).filter(User.email == email).first()


crud_user = CRUDUser()
