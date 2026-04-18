from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.common.auth import Hash, create_token
from app.common.api_logging import logger
from app.common.database import get_db
from app.common import constant
from app import schema, messages
from app.api.api_v1.utils import utils

router = APIRouter()

@router.post("/sign_up", response_model=schema.TokenResponse, status_code=status.HTTP_201_CREATED)
def signup(request: schema.SignUpRequest, db: Session = Depends(get_db)):
    """
    Register a new user and generate an access token.
    """
    try:

        user_data = utils.get_user_details(db,request)
        if user_data:
            logger.error(messages.USER_ALREADY_REGISTERED)
            return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"detail": messages.USER_ALREADY_REGISTERED}
            )

        if not utils.is_valid_password(request.password):
            logger.error(messages.PASSWORD_VALIDATION_ERROR)
            return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": messages.PASSWORD_VALIDATION_ERROR}
            )

        request.password = Hash.encode_password(request.password)
        new_user = utils.save_user_details(db, request)
        new_user_dict = {
            "id": str(new_user.id),
            "first_name": new_user.first_name,
            "last_name": new_user.last_name,
            "email": new_user.email,
        }
        jwt_token = create_token(new_user_dict)
        token_obj = utils.create_token_object(jwt_token)
        logger.info("Customer sign up successful. Sending jwt token")
        return token_obj
    except Exception as e:
        raise HTTPException(
        status_code=400,
        detail=str(e))
    finally:
        db.close()


@router.post("/sign_in", response_model=schema.TokenResponse, status_code=status.HTTP_200_OK)
def sign_in(request: schema.SignInRequest, db: Session = Depends(get_db)):

    """Authenticate a user and generate an access token."""
    try:
        logger.info(f"Received sign in request: {request.email}")
        user_data = utils.get_user_details(db,request)
        if not user_data:
            logger.error(f"Error: User with email {request.email} not found")
            return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": messages.USER_NOT_REGISTERED}
            )
            
        elif not Hash.verify(user_data.encrypted_password, request.password):
            logger.error("Error: Password veification failed")
            return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": messages.INCORRECT_PASSWORD}
            )
        else:
            user_dict = {
            "id": str(user_data.id),
            "first_name": user_data.first_name,
            "last_name": user_data.last_name,
            "email": user_data.email,
        }
            jwt_token = create_token(user_dict)
            token_obj = utils.create_token_object(jwt_token)
            logger.info("Customer sign in successful. Sending jwt token")
            return token_obj
    except Exception as e:
        raise HTTPException(
        status_code=400,
        detail=str(e))
    finally:
        db.close()