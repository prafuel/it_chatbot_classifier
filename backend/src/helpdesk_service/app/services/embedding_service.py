"""
Embedding Service — generates and stores vector embeddings for KB articles.

Uses sentence-transformers (all-MiniLM-L6-v2, 384 dims) for local embedding
generation and pgvector for storage.
"""

import logging
from typing import List, Optional

from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sentence_transformers import SentenceTransformer

from app.common.models import KnowledgeBase, KBEmbedding, Category

logger = logging.getLogger(__name__)

# Load model once at module level (cached in Docker image)
_model: Optional[SentenceTransformer] = None


def _get_model() -> SentenceTransformer:
    """Lazy-load the embedding model."""
    global _model
    if _model is None:
        logger.info("Loading embedding model: all-MiniLM-L6-v2 ...")
        _model = SentenceTransformer("all-MiniLM-L6-v2")
        logger.info("Embedding model loaded.")
    return _model


def generate_embedding(text: str) -> List[float]:
    """Generate a 384-dim embedding vector for the given text."""
    model = _get_model()
    return model.encode(text, normalize_embeddings=True).tolist()


def _build_content_text(kb: KnowledgeBase) -> str:
    """Concatenate KB fields into a single text block for embedding."""
    parts = [kb.title, kb.problem_description, kb.solution_steps]
    return ". ".join(p for p in parts if p)


def build_kb_embeddings(db: Session) -> dict:
    """
    Bulk-generate embeddings for all approved KB articles.
    Uses upsert (ON CONFLICT kb_id DO UPDATE) so re-runs are safe.
    Returns counts of inserted and updated rows.
    """
    articles = (
        db.query(KnowledgeBase)
        .filter(KnowledgeBase.approved == True)
        .all()
    )

    if not articles:
        logger.info("No approved KB articles found.")
        return {"total": 0, "processed": 0}

    # Pre-fetch category names for denormalization
    categories = {c.category_id: c.name for c in db.query(Category).all()}

    processed = 0
    for kb in articles:
        content_text = _build_content_text(kb)
        embedding = generate_embedding(content_text)
        category_name = categories.get(kb.category_id)

        stmt = pg_insert(KBEmbedding.__table__).values(
            kb_id=kb.kb_id,
            embedding=embedding,
            content_text=content_text,
            category_name=category_name,
            sub_category_name=None,  # can be enriched later
        ).on_conflict_do_update(
            index_elements=["kb_id"],
            set_={
                "embedding": embedding,
                "content_text": content_text,
                "category_name": category_name,
            },
        )
        db.execute(stmt)
        processed += 1

        if processed % 10 == 0:
            logger.info(f"Embedded {processed}/{len(articles)} KB articles...")

    db.commit()
    logger.info(f"Embedding build complete: {processed} articles processed.")
    return {"total": len(articles), "processed": processed}
