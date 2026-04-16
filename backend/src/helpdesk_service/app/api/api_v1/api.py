"""
Main API router — aggregates all endpoint routers.
"""

from fastapi import APIRouter

from app.api.api_v1.endpoints.tickets import router as tickets_router
from app.api.api_v1.endpoints.categories import router as categories_router
from app.api.api_v1.endpoints.knowledge_base import router as kb_router
from app.api.api_v1.endpoints.comments import router as comments_router
from app.api.api_v1.endpoints.dashboard import router as dashboard_router

router = APIRouter()

router.include_router(tickets_router)
router.include_router(categories_router)
router.include_router(kb_router)
router.include_router(comments_router)
router.include_router(dashboard_router)
