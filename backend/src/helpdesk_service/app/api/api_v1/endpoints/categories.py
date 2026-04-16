"""
Category API endpoints.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.common.database import get_db
from app.crud import crud_category
from app import schema

router = APIRouter(prefix="/categories", tags=["Categories"])


@router.post("/", response_model=schema.CategoryResponse, status_code=status.HTTP_201_CREATED)
def create_category(payload: schema.CategoryBase, db: Session = Depends(get_db)):
    """Create a new category."""
    return crud_category.create_category(db, payload.name)


@router.get("/", response_model=list[schema.CategoryResponse])
def list_categories(db: Session = Depends(get_db)):
    """List all categories."""
    return crud_category.list_categories(db)


@router.post(
    "/{category_id}/subcategories/",
    response_model=schema.SubCategoryResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_subcategory(
    category_id: uuid.UUID,
    payload: schema.SubCategoryCreate,
    db: Session = Depends(get_db),
):
    """Create a subcategory under a category."""
    cat = crud_category.get_category(db, category_id)
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")
    return crud_category.create_sub_category(db, category_id, payload.name)


@router.get("/{category_id}/subcategories/", response_model=list[schema.SubCategoryResponse])
def list_subcategories(category_id: uuid.UUID, db: Session = Depends(get_db)):
    """List subcategories for a category."""
    return crud_category.list_sub_categories(db, category_id)
