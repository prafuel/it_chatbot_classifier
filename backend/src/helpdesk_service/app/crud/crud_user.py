from sqlalchemy.orm import Session
from datetime import datetime
from app.common.models import User
from app.schema import SignUpRequest

class CRUDUser:
    def create_user(self, db: Session, user_data: SignUpRequest):
        new_user = User(
            name=f"{user_data.first_name} {user_data.last_name}",
            email=user_data.email,
            encrypted_password=user_data.password,
            created_at=datetime.utcnow()
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return new_user

    def get_user_by_email(self, db: Session, email: str):
        return db.query(User).filter(User.email == email).first()


crud_user = CRUDUser()
