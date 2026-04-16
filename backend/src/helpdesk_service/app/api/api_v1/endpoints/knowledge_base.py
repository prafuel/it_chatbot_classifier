"""
Knowledge Base API endpoints.
"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.common.database import get_db
from app.crud import crud_knowledge_base
from app import schema

router = APIRouter(prefix="/kb", tags=["Knowledge Base"])


@router.post("/", response_model=schema.KnowledgeBaseResponse, status_code=status.HTTP_201_CREATED)
def create_kb_article(payload: schema.KnowledgeBaseCreate, db: Session = Depends(get_db)):
    """Create a new knowledge base article (unapproved by default)."""
    return crud_knowledge_base.create_kb_article(
        db=db,
        title=payload.title,
        problem_description=payload.problem_description,
        solution_steps=payload.solution_steps,
        created_by=payload.created_by,
        category_id=payload.category_id,
        tags=payload.tags,
    )


@router.get("/", response_model=list[schema.KnowledgeBaseResponse])
def list_kb_articles(
    approved_only: bool = Query(False),
    category_id: Optional[uuid.UUID] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """List knowledge base articles."""
    return crud_knowledge_base.list_kb_articles(
        db, approved_only=approved_only, category_id=category_id, skip=skip, limit=limit,
    )


@router.get("/search", response_model=list[schema.KnowledgeBaseResponse])
def search_kb(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """Search approved KB articles by keyword."""
    return crud_knowledge_base.search_kb(db, q, limit=limit)


@router.get("/{kb_id}", response_model=schema.KnowledgeBaseResponse)
def get_kb_article(kb_id: uuid.UUID, db: Session = Depends(get_db)):
    """Get a single KB article."""
    article = crud_knowledge_base.get_kb_article(db, kb_id)
    if not article:
        raise HTTPException(status_code=404, detail="KB article not found")
    return article


@router.patch("/{kb_id}/approve", response_model=schema.KnowledgeBaseResponse)
def approve_kb_article(kb_id: uuid.UUID, db: Session = Depends(get_db)):
    """Approve a KB article for public visibility."""
    article = crud_knowledge_base.approve_kb_article(db, kb_id)
    if not article:
        raise HTTPException(status_code=404, detail="KB article not found")
    return article
