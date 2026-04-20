"""
CRUD operations for Categories and SubCategories.
"""

import uuid
import logging
from typing import Optional, List

from sqlalchemy.orm import Session

from app.common.models import Category, SubCategory

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Categories
# ---------------------------------------------------------------------------

def create_category(db: Session, name: str) -> Category:
    category = Category(name=name)
    db.add(category)
    db.commit()
    db.refresh(category)
    logger.info(f"Category created: {category.category_id} - {name}")
    return category


def get_category(db: Session, category_id: uuid.UUID) -> Optional[Category]:
    return db.query(Category).filter(Category.category_id == category_id).first()


def list_categories(db: Session) -> List[Category]:
    return db.query(Category).order_by(Category.name).all()


# ---------------------------------------------------------------------------
# SubCategories
# ---------------------------------------------------------------------------

def create_sub_category(
    db: Session, category_id: uuid.UUID, name: str
) -> SubCategory:
    sub = SubCategory(category_id=category_id, name=name)
    db.add(sub)
    db.commit()
    db.refresh(sub)
    logger.info(f"SubCategory created: {sub.sub_category_id} under {category_id}")
    return sub


def get_sub_category(db: Session, sub_category_id: uuid.UUID) -> Optional[SubCategory]:
    return (
        db.query(SubCategory)
        .filter(SubCategory.sub_category_id == sub_category_id)
        .first()
    )


def list_sub_categories(
    db: Session, category_id: uuid.UUID
) -> List[SubCategory]:
    return (
        db.query(SubCategory)
        .filter(SubCategory.category_id == category_id)
        .order_by(SubCategory.name)
        .all()
    )
