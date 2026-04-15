import os
import jwt
from datetime import datetime, timedelta
from fastapi import HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.common import api_logging

logger = api_logging.logger

# ---------------------------------------------------------------------------
# JWT Configuration (read from env, with sensible defaults)
# ---------------------------------------------------------------------------
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "acl-chatbot-change-me-in-production-secret-key-2026")
JWT_ALGORITHM  = "HS256"
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "60"))

# In-memory blacklist for logout
token_blacklist: set[str] = set()


# ---------------------------------------------------------------------------
# Token creation
# ---------------------------------------------------------------------------

def create_access_token() -> str:
    """Create a JWT token for the single admin user."""
    payload = {
        "sub": "admin",
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(minutes=JWT_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


# ---------------------------------------------------------------------------
# Token invalidation (logout)
# ---------------------------------------------------------------------------

def invalidate_token(token: str) -> None:
    """Add token to the in-memory blacklist."""
    token_blacklist.add(token)
    logger.info("Admin token invalidated")


# ---------------------------------------------------------------------------
# JWT Bearer dependency
# ---------------------------------------------------------------------------

class JWTBearer(HTTPBearer):
    """FastAPI dependency that validates the Bearer JWT on protected routes."""

    def __init__(self, auto_error: bool = True):
        super().__init__(auto_error=auto_error)

    async def __call__(self, request: Request) -> dict:
        credentials: HTTPAuthorizationCredentials = await super().__call__(request)

        if not credentials or credentials.scheme.lower() != "bearer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication scheme",
            )

        payload = self._decode(credentials.credentials)
        payload["_raw_token"] = credentials.credentials
        return payload

    def _decode(self, token: str) -> dict:
        if token in token_blacklist:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been invalidated — please log in again",
            )
        try:
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
            if payload.get("sub") != "admin":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not an admin token",
                )
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
            )
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
            )
