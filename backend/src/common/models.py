"""
SQLAlchemy ORM models for IT Support services.
"""

import enum
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any

from sqlalchemy import Column, String, Float, Text, DateTime, ForeignKey, Boolean, Enum, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base, object_session, relationship, synonym
from sqlalchemy.ext.declarative import declared_attr
from pgvector.sqlalchemy import Vector

from app.common.database import Base


class RoleEnum(str, enum.Enum):
    USER = "USER"
    IT_AGENT = "IT_AGENT"
    ADMIN = "ADMIN"

class StatusEnum(str, enum.Enum):
    NOT_ASSIGNED = "NOT_ASSIGNED"
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"

class PriorityEnum(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class SourceEnum(str, enum.Enum):
    chatbot = "chatbot"
    portal = "portal"
    email = "email"

class ApprovalStatusEnum(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    NA = "NA"


# Association table for Agent Specializations (Many-to-Many)
class AgentSpecialization(Base):
    __tablename__ = "agent_specializations"
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), primary_key=True)
    category_id = Column(UUID(as_uuid=True), ForeignKey("categories.category_id"), primary_key=True)


class User(Base):
    __tablename__ = "users"
    
    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    id = synonym("user_id")
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    name = Column(String(255), nullable=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    encrypted_password = Column(String(255), nullable=True)
    role = Column(Enum(RoleEnum), default=RoleEnum.USER)
    is_available = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    specializations = relationship("Category", secondary="agent_specializations", backref="specialized_agents")


class Category(Base):
    __tablename__ = "categories"
    
    category_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), unique=True, nullable=False)


class SubCategory(Base):
    __tablename__ = "sub_categories"
    
    sub_category_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    category_id = Column(UUID(as_uuid=True), ForeignKey("categories.category_id"), nullable=False)
    name = Column(String(255), nullable=False)


class Ticket(Base):
    __tablename__ = "tickets"
    
    ticket_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    status = Column(Enum(StatusEnum), default=StatusEnum.NOT_ASSIGNED)
    priority = Column(Enum(PriorityEnum), default=PriorityEnum.MEDIUM)
    category_id = Column(UUID(as_uuid=True), ForeignKey("categories.category_id"), nullable=True)
    sub_category_id = Column(UUID(as_uuid=True), ForeignKey("sub_categories.sub_category_id"), nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    assigned_to = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=True)
    
    # Approval fields
    needs_approval = Column(Boolean, default=False)
    approver_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=True)
    designated_approver_type = Column(String(255), nullable=True)
    approval_status = Column(Enum(ApprovalStatusEnum), default=ApprovalStatusEnum.NA)
    approval_requested_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)
    sla_due_at = Column(DateTime, nullable=True)
    source = Column(Enum(SourceEnum), default=SourceEnum.chatbot)

    assigned_user = relationship("User", foreign_keys=[assigned_to], lazy="joined")
    approver_user = relationship("User", foreign_keys=[approver_id], lazy="joined")

    @property
    def assigned_to_name(self) -> Optional[str]:
        if self.assigned_user:
            return f"{self.assigned_user.first_name} {self.assigned_user.last_name}" if self.assigned_user.first_name else self.assigned_user.name
        return None

    @property
    def approver_name(self) -> Optional[str]:
        if self.approver_user:
            return f"{self.approver_user.first_name} {self.approver_user.last_name}" if self.approver_user.first_name else self.approver_user.name
        return None


class TicketComment(Base):
    __tablename__ = "ticket_comments"
    
    comment_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticket_id = Column(UUID(as_uuid=True), ForeignKey("tickets.ticket_id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    comment_text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class KnowledgeBase(Base):
    __tablename__ = "knowledge_base"
    
    kb_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=False)
    problem_description = Column(Text, nullable=False)
    solution_steps = Column(Text, nullable=False)
    category_id = Column(UUID(as_uuid=True), ForeignKey("categories.category_id"), nullable=True)
    tags = Column(JSON, nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    approved = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class KBEmbedding(Base):
    """Stores pgvector embeddings for knowledge base articles."""
    __tablename__ = "kb_embeddings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    kb_id = Column(UUID(as_uuid=True), ForeignKey("knowledge_base.kb_id"), nullable=False, unique=True)
    embedding = Column(Vector(384), nullable=False)  # all-MiniLM-L6-v2 output
    content_text = Column(Text, nullable=False)       # concatenated text used for embedding
    category_name = Column(String(255), nullable=True)
    sub_category_name = Column(String(255), nullable=True)