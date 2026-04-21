"""
Auth endpoints — sign_up and sign_in (migrated from usermanagementservice).
"""
import re

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.common.auth import Hash, create_token
from app.common.api_logging import logger
from app.common.database import get_db
from app.auth_schema import SignUpRequest, SignInRequest, TokenResponse
from app.auth_crud import crud_user
import app.auth_messages as messages

router = APIRouter(tags=["auth"])


def _is_valid_password(password: str) -> bool:
    reg = r"^(?=.*[0-9])(?=.*[a-z])(?=.*[A-Z])(?=.*\W)(?!.* ).{6,}$"
    return bool(re.search(reg, password))


@router.post(
    "/sign_up",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
def sign_up(request: SignUpRequest, db: Session = Depends(get_db)):
    """Register a new user and return a JWT access token."""
    try:
        existing = crud_user.get_user_by_email(db, request.email)
        if existing:
            logger.error(messages.USER_ALREADY_REGISTERED)
            return JSONResponse(
                status_code=status.HTTP_409_CONFLICT,
                content={"detail": messages.USER_ALREADY_REGISTERED},
            )

        if not _is_valid_password(request.password):
            logger.error(messages.PASSWORD_VALIDATION_ERROR)
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"detail": messages.PASSWORD_VALIDATION_ERROR},
            )

        request.password = Hash.encode_password(request.password)
        new_user = crud_user.create_user(db, request)

        payload = {
            "id": str(new_user.id or new_user.user_id),
            "first_name": new_user.first_name,
            "last_name": new_user.last_name,
            "email": new_user.email,
        }
        jwt_token = create_token(payload)
        logger.info("User sign-up successful")
        return TokenResponse(
            token=jwt_token,
            token_type="Bearer",
            user_type=new_user.role.value if new_user.role else "USER",
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        db.close()


@router.post(
    "/sign_in",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Authenticate an existing user",
)
def sign_in(request: SignInRequest, db: Session = Depends(get_db)):
    """Authenticate a user and return a JWT access token."""
    try:
        logger.info(f"Sign-in attempt for: {request.email}")
        user = crud_user.get_user_by_email(db, request.email)

        if not user:
            logger.error(f"User not found: {request.email}")
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": messages.USER_NOT_REGISTERED},
            )

        if not Hash.verify(user.encrypted_password, request.password):
            logger.error("Password verification failed")
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": messages.INCORRECT_PASSWORD},
            )

        payload = {
            "id": str(user.id or user.user_id),
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
        }
        jwt_token = create_token(payload)
        logger.info("User sign-in successful")
        return TokenResponse(
            token=jwt_token,
            token_type="Bearer",
            user_type=user.role.value if user.role else "USER",
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        db.close()
