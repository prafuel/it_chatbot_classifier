"""
CRUD operations for the Knowledge Base.
"""

import uuid
import logging
from typing import Optional, List

from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.common.models import KnowledgeBase

logger = logging.getLogger(__name__)


def create_kb_article(
    db: Session,
    title: str,
    problem_description: str,
    solution_steps: str,
    created_by: uuid.UUID,
    category_id: Optional[uuid.UUID] = None,
    tags: Optional[list] = None,
) -> KnowledgeBase:
    article = KnowledgeBase(
        title=title,
        problem_description=problem_description,
        solution_steps=solution_steps,
        created_by=created_by,
        category_id=category_id,
        tags=tags,
        approved=False,
    )
    db.add(article)
    db.commit()
    db.refresh(article)
    logger.info(f"KB article created: {article.kb_id}")
    return article


def get_kb_article(db: Session, kb_id: uuid.UUID) -> Optional[KnowledgeBase]:
    return db.query(KnowledgeBase).filter(KnowledgeBase.kb_id == kb_id).first()


def list_kb_articles(
    db: Session,
    approved_only: bool = False,
    category_id: Optional[uuid.UUID] = None,
    skip: int = 0,
    limit: int = 50,
) -> List[KnowledgeBase]:
    query = db.query(KnowledgeBase)
    if approved_only:
        query = query.filter(KnowledgeBase.approved == True)
    if category_id:
        query = query.filter(KnowledgeBase.category_id == category_id)
    return query.order_by(KnowledgeBase.created_at.desc()).offset(skip).limit(limit).all()


def search_kb(db: Session, query_text: str, limit: int = 10) -> List[KnowledgeBase]:
    """
    Keyword search across title, problem_description.
    Only returns approved articles.
    """
    pattern = f"%{query_text}%"
    return (
        db.query(KnowledgeBase)
        .filter(KnowledgeBase.approved == True)
        .filter(
            or_(
                KnowledgeBase.title.ilike(pattern),
                KnowledgeBase.problem_description.ilike(pattern),
            )
        )
        .limit(limit)
        .all()
    )


def approve_kb_article(db: Session, kb_id: uuid.UUID) -> Optional[KnowledgeBase]:
    article = get_kb_article(db, kb_id)
    if not article:
        return None
    article.approved = True
    db.commit()
    db.refresh(article)
    logger.info(f"KB article approved: {kb_id}")
    return article
