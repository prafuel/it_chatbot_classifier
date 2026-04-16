import uuid
from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any
from enum import Enum


class StatusEnum(str, Enum):
    NOT_ASSIGNED = "NOT_ASSIGNED"
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"

class PriorityEnum(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class SourceEnum(str, Enum):
    chatbot = "chatbot"
    portal = "portal"
    email = "email"


class CategoryBase(BaseModel):
    name: str

class CategoryResponse(CategoryBase):
    category_id: uuid.UUID

    class Config:
        from_attributes = True


class SubCategoryBase(BaseModel):
    name: str
    category_id: uuid.UUID

class SubCategoryResponse(SubCategoryBase):
    sub_category_id: uuid.UUID

    class Config:
        from_attributes = True


class TicketBase(BaseModel):
    title: str
    description: str
    priority: PriorityEnum = PriorityEnum.MEDIUM
    category_id: Optional[uuid.UUID] = None
    sub_category_id: Optional[uuid.UUID] = None
    source: SourceEnum = SourceEnum.chatbot

class TicketCreate(TicketBase):
    created_by: uuid.UUID

class TicketResponse(TicketBase):
    ticket_id: uuid.UUID
    status: StatusEnum
    created_by: uuid.UUID
    assigned_to: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime] = None
    sla_due_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TicketCommentBase(BaseModel):
    comment_text: str
    ticket_id: uuid.UUID
    user_id: uuid.UUID

class TicketCommentCreate(TicketCommentBase):
    pass

class TicketCommentResponse(TicketCommentBase):
    comment_id: uuid.UUID
    created_at: datetime

    class Config:
        from_attributes = True


class KnowledgeBaseBase(BaseModel):
    title: str
    problem_description: str
    solution_steps: str
    category_id: Optional[uuid.UUID] = None
    tags: Optional[Any] = None

class KnowledgeBaseCreate(KnowledgeBaseBase):
    created_by: uuid.UUID

class KnowledgeBaseResponse(KnowledgeBaseBase):
    kb_id: uuid.UUID
    created_by: uuid.UUID
    approved: bool
    created_at: datetime

    class Config:
        from_attributes = True
