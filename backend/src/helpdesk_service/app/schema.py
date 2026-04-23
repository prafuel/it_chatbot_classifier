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

class ApprovalStatusEnum(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    NA = "NA"


# ---------------------------------------------------------------------------
# Categories
# ---------------------------------------------------------------------------

class CategoryBase(BaseModel):
    name: str

class CategoryResponse(CategoryBase):
    category_id: uuid.UUID

    class Config:
        from_attributes = True


class SubCategoryCreate(BaseModel):
    name: str

class SubCategoryBase(BaseModel):
    name: str
    category_id: uuid.UUID

class SubCategoryResponse(SubCategoryBase):
    sub_category_id: uuid.UUID

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Tickets
# ---------------------------------------------------------------------------

class TicketBase(BaseModel):
    title: str
    description: str
    priority: PriorityEnum = PriorityEnum.MEDIUM
    category_id: Optional[uuid.UUID] = None
    sub_category_id: Optional[uuid.UUID] = None
    source: SourceEnum = SourceEnum.chatbot

class TicketCreate(TicketBase):
    pass

class TicketUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[PriorityEnum] = None
    category_id: Optional[uuid.UUID] = None
    sub_category_id: Optional[uuid.UUID] = None

class TicketStatusUpdate(BaseModel):
    status: StatusEnum

class TicketAssign(BaseModel):
    assigned_to: uuid.UUID

class TicketResponse(TicketBase):
    ticket_id: uuid.UUID
    status: StatusEnum
    created_by: uuid.UUID
    assigned_to: Optional[uuid.UUID] = None
    assigned_to_name: Optional[str] = None
    
    # Approval fields
    needs_approval: bool
    approver_id: Optional[uuid.UUID] = None
    approver_name: Optional[str] = None
    designated_approver_type: Optional[str] = None
    approval_status: ApprovalStatusEnum
    
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime] = None
    sla_due_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Comments
# ---------------------------------------------------------------------------

class TicketCommentCreate(BaseModel):
    comment_text: str

class TicketCommentResponse(BaseModel):
    comment_id: uuid.UUID
    ticket_id: uuid.UUID
    user_id: uuid.UUID
    comment_text: str
    created_at: datetime

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Knowledge Base
# ---------------------------------------------------------------------------

class KnowledgeBaseBase(BaseModel):
    title: str
    problem_description: str
    solution_steps: str
    category_id: Optional[uuid.UUID] = None
    tags: Optional[Any] = None

class KnowledgeBaseCreate(KnowledgeBaseBase):
    pass

class KnowledgeBaseResponse(KnowledgeBaseBase):
    kb_id: uuid.UUID
    created_by: uuid.UUID
    approved: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# AI Query
# ---------------------------------------------------------------------------

class QueryRequest(BaseModel):
    query: str

class KBSourceItem(BaseModel):
    kb_id: str
    title: str
    category: Optional[str] = None
    similarity: float

class QueryResponse(BaseModel):
    query: str
    answer: str
    sources: list[KBSourceItem]
    category_detected: Optional[str] = None

class EmbeddingBuildResponse(BaseModel):
    total: int
    processed: int


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

class RoleEnum(str, Enum):
    USER = "USER"
    IT_AGENT = "IT_AGENT"
    ADMIN = "ADMIN"

class UserResponse(BaseModel):
    user_id: uuid.UUID
    name: str
    email: str
    role: RoleEnum
    is_available: bool
    specializations: List[CategoryResponse] = []
    created_at: datetime

    class Config:
        from_attributes = True
