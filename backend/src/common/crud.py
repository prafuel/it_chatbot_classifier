"""
CRUD operations for PostgreSQL — ChatSession table.
"""

import uuid
import logging
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.common.models import ChatSession

logger = logging.getLogger(__name__)

