"""
SQLAlchemy ORM models for IT Support services.
"""

import enum
import uuid
from datetime import datetime
from typing import Dict, List

from sqlalchemy import Column, String, Float, Text, DateTime, ForeignKey, Boolean, Enum, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base, object_session, relationship
from sqlalchemy.ext.declarative import declared_attr

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


class User(Base):
    __tablename__ = "users"
    
    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # Auth fields (migrated from usermanagementservice)
    id = Column(UUID(as_uuid=True), unique=True, default=uuid.uuid4)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    name = Column(String(255), nullable=True)
    encrypted_password = Column(String(255), nullable=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    role = Column(Enum(RoleEnum), default=RoleEnum.USER)
    is_available = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


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
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)
    sla_due_at = Column(DateTime, nullable=True)
    source = Column(Enum(SourceEnum), default=SourceEnum.chatbot)


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