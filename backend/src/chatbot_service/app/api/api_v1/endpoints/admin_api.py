import os
from fastapi import APIRouter, HTTPException, Depends, Request, status
from pydantic import BaseModel

from app.common import api_logging
from app.common.auth import (
    JWTBearer,
    create_access_token,
    invalidate_token,
)
from app.common.messages import LogMessages as Msg
from app.common.constant import (
    DEFAULT_TEXT_FAISS_INDEX_PATH,
    DEFAULT_TEXT_IDS_PATH,
)
from app import schema
from app.utils.bot_utils.text_knowledge import ingest_admin_text

logger = api_logging.logger
router = APIRouter()


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class AdminLoginRequest(BaseModel):
    username: str = "admin"
    password: str = "admin"


class AdminLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class AdminLogoutResponse(BaseModel):
    message: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_admin_credentials() -> tuple[str, str]:
    """Read admin credentials from environment variables."""
    admin_user = os.getenv("ADMIN")
    admin_pass = os.getenv("PASSWORD")
    if not admin_user or not admin_pass:
        logger.error("ADMIN or PASSWORD env variable is not set")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Admin credentials are not configured on the server",
        )
    return admin_user, admin_pass


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/login",
    response_model=AdminLoginResponse,
    status_code=status.HTTP_200_OK,
    summary="Admin Login",
)
async def admin_login(body: AdminLoginRequest):
    """
    Authenticate the admin using ADMIN and PASSWORD env variables.
    Returns a JWT access token on success.
    """
    expected_username, expected_password = _get_admin_credentials()

    if body.username != expected_username or body.password != expected_password:
        logger.warning(f"Failed admin login attempt for username: '{body.username}'")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    token = create_access_token()
    logger.info("Admin login successful")
    return AdminLoginResponse(access_token=token)


@router.post(
    "/logout",
    response_model=AdminLogoutResponse,
    status_code=status.HTTP_200_OK,
    summary="Admin Logout",
    dependencies=[Depends(JWTBearer())],
)
async def admin_logout(payload: dict = Depends(JWTBearer())):
    """
    Invalidate the current JWT token (adds it to the in-memory blacklist).
    Requires a valid Bearer token.
    """
    raw_token = payload.get("_raw_token")
    if raw_token:
        invalidate_token(raw_token)

    logger.info("Admin logout successful — token invalidated")
    return AdminLogoutResponse(message="Logged out successfully")


# ---------------------------------------------------------------------------
# Knowledge ingestion
# ---------------------------------------------------------------------------

@router.post(
    "/knowledge",
    response_model=schema.AdminTextResponse,
    status_code=status.HTTP_200_OK,
    summary="Ingest extra textual knowledge",
    dependencies=[Depends(JWTBearer())],
)
async def ingest_knowledge(request: Request, body: schema.AdminTextRequest):
    """
    Accept arbitrary text from the admin, chunk it, embed it into a
    separate FAISS index (or merge into an existing one), and update
    the in-memory state so future queries benefit immediately.
    Requires admin JWT.
    """
    raw_text = body.text.strip()
    if not raw_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=Msg.TEXT_EMPTY_DETAIL,
        )

    # Resolve paths
    text_index_path = os.getenv("TEXT_FAISS_INDEX_PATH", DEFAULT_TEXT_FAISS_INDEX_PATH)
    text_ids_path = os.getenv("TEXT_IDS_PATH", DEFAULT_TEXT_IDS_PATH)

    model = getattr(request.app.state, "embedding_model", None)
    if model is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Embedding model is not loaded yet.",
        )

    try:
        updated_index, updated_chunks, num_new = ingest_admin_text(
            raw_text=raw_text,
            model=model,
            index_path=text_index_path,
            ids_path=text_ids_path,
        )

        # Hot-swap in-memory state (no restart needed)
        request.app.state.text_index = updated_index
        request.app.state.text_chunks = updated_chunks

        return schema.AdminTextResponse(
            message=f"Successfully ingested {num_new} text chunks.",
            num_chunks=num_new,
            index_path=text_index_path,
        )
    except Exception as exc:
        logger.error(Msg.TEXT_INGEST_ERROR.format(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to ingest text: {exc}",
        )
