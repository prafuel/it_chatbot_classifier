"""
Pydantic schemas for user authentication (migrated from usermanagementservice).
"""
from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, EmailStr, Field
from pydantic import field_validator


class SignUpRequest(BaseModel):
    first_name: str = Field(..., min_length=1, description="First Name")
    last_name: str = Field(..., min_length=1, description="Last Name")
    email: EmailStr = Field(..., description="Email")
    password: str = Field(..., min_length=1, description="Password")


class SignInRequest(BaseModel):
    email: EmailStr = Field(..., description="Email of the user")
    password: str = Field(..., min_length=1, description="Password")


class TokenResponse(BaseModel):
    token: Optional[str] = Field(None, description="JWT Token")
    token_type: Optional[str] = Field(None, description="Token Type")
    user_type: Optional[str] = Field(None, description="User role / type")


class RoleEnum(str, Enum):
    USER = "USER"
    IT_AGENT = "IT_AGENT"
    ADMIN = "ADMIN"


class UserResponse(BaseModel):
    user_id: uuid.UUID
    first_name: Optional[str]
    last_name: Optional[str]
    email: EmailStr
    role: RoleEnum
    is_available: bool
    created_at: datetime

    class Config:
        from_attributes = True
