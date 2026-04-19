"""
IT Support Helpdesk Service — FastAPI application entry point.
"""

import logging
import uvicorn
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends
from starlette.middleware.cors import CORSMiddleware

from app.common.database import get_db_engine, Base
from app.common import api_logging

# Import models so SQLAlchemy registers them before create_all
from app.common import models  # noqa: F401

from app.api.api_v1.api import router as api_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: ensure database and tables exist."""
    logger.info("Helpdesk Service starting up — creating database tables...")
    engine = get_db_engine()
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables ready.")
    yield
    logger.info("Helpdesk Service shutting down.")


app = FastAPI(
    title="IT Support Helpdesk Service",
    description="Enterprise IT Support Automation — Ticket Management, Knowledge Base, and Analytics",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    # allow_origins=["http://localhost:8080"], update when you want to deploy on local
    allow_origins=["https://support-sphere-two.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount all API routes
app.include_router(
    api_router,
    prefix="/api/v1/helpdesk",
    dependencies=[Depends(api_logging.logging_dependency)],
)


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "healthy", "service": "helpdesk"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=3000)
