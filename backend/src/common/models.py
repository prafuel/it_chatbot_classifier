"""
SQLAlchemy ORM models for ACL Chatbot services.
"""

import uuid
from datetime import datetime
from typing import Dict, List
from sqlalchemy import Column, String, Float, Text, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base, object_session
from sqlalchemy.ext.declarative import declared_attr

from app.common.database import Base


class ChatSession(Base):
    """Stores every chat interaction including user location and network info."""

    __tablename__ = "chat_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    # Network identity
    ip           = Column(String(64), nullable=True)

    # Location fields (flattened from UserLocationData)
    country      = Column(String(128), nullable=True)
    country_code = Column(String(16),  nullable=True)
    region       = Column(String(128), nullable=True)
    region_code  = Column(String(16),  nullable=True)
    city         = Column(String(128), nullable=True)
    zip          = Column(String(32),  nullable=True)
    lat          = Column(Float,       nullable=True)
    lon          = Column(Float,       nullable=True)
    timezone     = Column(String(64),  nullable=True)

    # Network provider fields (flattened from UserNetworkData)
    isp          = Column(String(256), nullable=True)
    organization = Column(String(256), nullable=True)
    asn          = Column(String(128), nullable=True)

    # Chat payload
    query        = Column(Text, nullable=False)
    response     = Column(Text, nullable=False)

    # Timestamp
    created_at   = Column(DateTime, default=datetime.utcnow, nullable=False)

    @property
    def chats(self) -> List[Dict[str, str]]:
        """Fetch all historical chats for this IP from the database."""
        session = object_session(self)
        if session and self.ip:
            history = (
                session.query(ChatSession)
                .filter(ChatSession.ip == self.ip)
                .order_by(ChatSession.created_at.asc())
                .all()
            )
            return [
                {"query": c.query, "response": c.response} for c in history
            ]
        
        # Fallback to current record if no session or IP (e.g. during object creation)
        return [{"query": self.query, "response": self.response}]