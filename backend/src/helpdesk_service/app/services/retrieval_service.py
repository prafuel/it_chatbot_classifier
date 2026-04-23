"""
Retrieval Service — vector similarity search against KB embeddings.

Uses pgvector's cosine distance operator for semantic search.
"""

import logging
from typing import List, Optional

from sqlalchemy.orm import Session
from sqlalchemy import text

from app.common.models import KBEmbedding, KnowledgeBase
from app.services.embedding_service import generate_embedding

logger = logging.getLogger(__name__)


def search_similar(
    db: Session,
    query_text: str,
    top_k: int = 5,
    category_filter: Optional[str] = None,
) -> List[dict]:
    """
    Embed the query and find the top-K most similar KB articles
    using pgvector cosine distance.

    Returns list of dicts with KB article data + similarity score.
    """
    query_embedding = generate_embedding(query_text)

    # Use SQLAlchemy ORM for pgvector cosine distance
    # distance = 0 means exact match, so similarity = 1 - distance
    distance_col = KBEmbedding.embedding.cosine_distance(query_embedding).label("distance")

    query = (
        db.query(KBEmbedding, KnowledgeBase, distance_col)
        .join(KnowledgeBase, KnowledgeBase.kb_id == KBEmbedding.kb_id)
        .filter(KnowledgeBase.approved == True)
    )

    if category_filter:
        query = query.filter(KBEmbedding.category_name == category_filter)

    query = query.order_by(distance_col).limit(top_k)
    rows = query.all()

    results = []
    for emb, kb, distance in rows:
        results.append({
            "kb_id": str(kb.kb_id),
            "title": kb.title,
            "problem_description": kb.problem_description,
            "solution_steps": kb.solution_steps,
            "category_name": emb.category_name,
            "sub_category_name": emb.sub_category_name,
            "tags": kb.tags,
            "similarity": round(1.0 - float(distance), 4) if distance is not None else 0.0,
        })

    logger.info(
        f"Vector search for '{query_text[:50]}...' returned {len(results)} results"
        + (f" (filtered by category: {category_filter})" if category_filter else "")
    )
    return results
