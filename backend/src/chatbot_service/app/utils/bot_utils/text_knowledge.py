"""
Text Knowledge Base — FAISS index for admin-uploaded textual content.

Admin can upload arbitrary text (job postings, FAQs, extra info).
The text is chunked, embedded, and stored in a separate FAISS index.
At query time the chatbot searches this index in parallel with the
graph-based index and merges up to TOP_K_TEXT_RETRIEVAL results into
the final LLM context.
"""

import os
import logging
import pickle

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

from app.common.messages import LogMessages as Msg
from app.common.constant import (
    TEXT_CHUNK_SIZE,
    TEXT_CHUNK_OVERLAP,
    TOP_K_TEXT_RETRIEVAL,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 1. Text Chunking
# ---------------------------------------------------------------------------
def chunk_text(
    text: str,
    chunk_size: int = TEXT_CHUNK_SIZE,
    overlap: int = TEXT_CHUNK_OVERLAP,
) -> list[str]:
    """Split *text* into overlapping chunks of roughly *chunk_size* words."""
    text = text.strip()
    if not text:
        return []

    words = text.split()
    chunks: list[str] = []
    
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunk_str = " ".join(words[start:end])
        chunks.append(chunk_str)
        start += (chunk_size - overlap)

    logger.info(Msg.TEXT_CHUNKED, len(chunks), chunk_size, overlap)
    return chunks


# ---------------------------------------------------------------------------
# 2. Build FAISS index from text chunks
# ---------------------------------------------------------------------------
def build_text_vector_index(
    text_chunks: list[str],
    model: SentenceTransformer,
) -> tuple[faiss.IndexFlatL2, list[str]]:
    """Encode *text_chunks* and build a FAISS IndexFlatL2."""
    try:
        if not text_chunks:
            raise ValueError("Empty text chunks — nothing to index")

        embeddings = model.encode(text_chunks, show_progress_bar=False, batch_size=64)
        embeddings = np.array(embeddings, dtype=np.float32)

        dim = embeddings.shape[1]
        index = faiss.IndexFlatL2(dim)
        index.add(embeddings)

        logger.info(Msg.TEXT_INDEX_BUILT, len(text_chunks), dim)
        return index, text_chunks
    except Exception as exc:
        logger.error(Msg.TEXT_INDEX_BUILD_ERROR.format(exc))
        raise


# ---------------------------------------------------------------------------
# 3. Save / Load text FAISS index
# ---------------------------------------------------------------------------
def save_text_vector_index(
    index: faiss.IndexFlatL2,
    text_chunks: list[str],
    index_path: str,
    ids_path: str,
) -> None:
    """Persist the text FAISS index and chunk list to disk."""
    try:
        os.makedirs(os.path.dirname(os.path.abspath(index_path)), exist_ok=True)
        os.makedirs(os.path.dirname(os.path.abspath(ids_path)), exist_ok=True)

        faiss.write_index(index, index_path)
        with open(ids_path, "wb") as fh:
            pickle.dump(text_chunks, fh)

        logger.info(Msg.TEXT_INDEX_SAVED, index_path, ids_path)
    except Exception as exc:
        logger.error(Msg.TEXT_INDEX_SAVE_FAILED, exc)


def load_text_vector_index(
    index_path: str,
    ids_path: str,
) -> tuple[faiss.IndexFlatL2, list[str]] | None:
    """Load a previously saved text FAISS index.  Returns None if not found."""
    if not os.path.exists(index_path) or not os.path.exists(ids_path):
        return None
    try:
        index = faiss.read_index(index_path)
        with open(ids_path, "rb") as fh:
            text_chunks = pickle.load(fh)
        logger.info(Msg.TEXT_INDEX_LOADED, index_path, ids_path)
        return index, text_chunks
    except Exception as exc:
        logger.error(Msg.TEXT_INDEX_LOAD_FAILED, index_path, ids_path, exc)
        return None


# ---------------------------------------------------------------------------
# 4. Search text FAISS index
# ---------------------------------------------------------------------------
def search_text_index(
    query: str,
    model: SentenceTransformer,
    index: faiss.IndexFlatL2,
    text_chunks: list[str],
    top_k: int = TOP_K_TEXT_RETRIEVAL,
) -> list[str]:
    """Return up to *top_k* text chunks most similar to *query*."""
    try:
        query_embedding = model.encode([query])
        query_embedding = np.array(query_embedding, dtype=np.float32)

        # Clamp top_k to the number of vectors actually in the index
        effective_k = min(top_k, index.ntotal)
        if effective_k == 0:
            return []

        distances, indices = index.search(query_embedding, effective_k)
        results = [
            text_chunks[i]
            for i in indices[0]
            if 0 <= i < len(text_chunks)
        ]

        logger.info(Msg.TEXT_SEARCH_RESULTS, len(results))
        return results
    except Exception as exc:
        logger.error(Msg.TEXT_SEARCH_FAILED, query, exc)
        return []


# ---------------------------------------------------------------------------
# 5. Ingest admin text (incremental merge)
# ---------------------------------------------------------------------------
def ingest_admin_text(
    raw_text: str,
    model: SentenceTransformer,
    index_path: str,
    ids_path: str,
) -> tuple[faiss.IndexFlatL2, list[str], int]:
    """
    Chunk *raw_text*, embed, and merge into any existing text FAISS index.

    Returns (updated_index, updated_chunks, num_new_chunks).
    """
    try:
        new_chunks = chunk_text(raw_text)
        if not new_chunks:
            raise ValueError("Text produced zero chunks after splitting")

        # Load existing index (if any) and merge
        existing = load_text_vector_index(index_path, ids_path)
        if existing is not None:
            existing_index, existing_chunks = existing
            # Encode only the new chunks
            new_embeddings = model.encode(new_chunks, show_progress_bar=False, batch_size=64)
            new_embeddings = np.array(new_embeddings, dtype=np.float32)
            existing_index.add(new_embeddings)
            merged_chunks = existing_chunks + new_chunks
            index, text_chunks = existing_index, merged_chunks
        else:
            index, text_chunks = build_text_vector_index(new_chunks, model)

        # Save merged index
        save_text_vector_index(index, text_chunks, index_path, ids_path)

        logger.info(Msg.TEXT_INGEST_SUCCESS, len(new_chunks), index_path)
        return index, text_chunks, len(new_chunks)
    except Exception as exc:
        logger.error(Msg.TEXT_INGEST_ERROR.format(exc))
        raise
