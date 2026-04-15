from fastapi import APIRouter
from app.api.api_v1.endpoints.chatbot_api import router as chatbot_router
from app.api.api_v1.endpoints.admin_api import router as admin_router

router = APIRouter()
router.include_router(chatbot_router, prefix="/chatbot", tags=["Chatbot"])
router.include_router(admin_router, prefix="/admin", tags=["Admin"])