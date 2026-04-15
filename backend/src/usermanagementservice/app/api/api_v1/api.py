# ************************************************************
# (C) Copyright 2023 , Inc. All rights reserved.
#
# ************************************************************

from fastapi import APIRouter
from app.api.api_v1.endpoints.usermanagementservice import router as usermanagement_api_router

router = APIRouter()
router.include_router(usermanagement_api_router)
