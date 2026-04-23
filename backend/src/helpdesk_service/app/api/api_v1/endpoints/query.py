"""
Query API endpoints — AI-powered knowledge retrieval.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.common.database import get_db
from app.common.models import User
from app.common.auth import get_current_user, get_it_staff_user, get_admin_user
from app.services import embedding_service, retrieval_service, llm_service
from app import schema

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/query", tags=["AI Query"])


@router.post("/", response_model=schema.QueryResponse)
def query_knowledge_base(
    payload: schema.QueryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    User submits a question → vector search KB → LLM generates answer.
    Accessible to all logged-in Users and IT Agents.
    """
    query_text = payload.query
    category_filter = None
    
    # --- Developer Configuration ---
    USE_CLASSIFICATION = True
    TOP_K = 5
    # -------------------------------

    # Step 1 (optional): Soft-classify to get category for filtered search
    if USE_CLASSIFICATION:
        classification = llm_service.classify_query(query_text)
        category_filter = classification.get("category")
        logger.info(f"LLM classification: {classification}")

    # Step 2: Vector similarity search
    kb_results = retrieval_service.search_similar(
        db=db,
        query_text=query_text,
        top_k=TOP_K,
        category_filter=category_filter,
    )

    # Step 3: LLM answer generation
    answer = llm_service.generate_answer(query_text, kb_results)

    return schema.QueryResponse(
        query=query_text,
        answer=answer,
        sources=[
            schema.KBSourceItem(
                kb_id=r["kb_id"],
                title=r["title"],
                category=r.get("category_name"),
                similarity=r["similarity"],
            )
            for r in kb_results
        ],
        category_detected=category_filter,
    )


@router.post(
    "/build-embeddings",
    response_model=schema.EmbeddingBuildResponse,
    status_code=status.HTTP_200_OK,
)
def build_embeddings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user),
):
    """
    Admin endpoint: bulk-generate embeddings for all approved KB articles.
    Safe to re-run (uses upsert). (IT Staff Only)
    """
    result = embedding_service.build_kb_embeddings(db)
    return schema.EmbeddingBuildResponse(**result)
