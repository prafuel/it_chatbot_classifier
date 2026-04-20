"""
Top-level Query API endpoint for knowledge base search.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from app.common.database import get_db
from app.crud import crud_knowledge_base
from app import schema

router = APIRouter(tags=["Query"])

@router.post("/query/", response_model=List[schema.KnowledgeBaseResponse])
def query_kb(payload: schema.KnowledgeBaseQueryRequest, db: Session = Depends(get_db)):
    """
    Search into knowledge base and return results accordingly.
    """
    return crud_knowledge_base.search_kb(db, payload.query, limit=payload.limit)
