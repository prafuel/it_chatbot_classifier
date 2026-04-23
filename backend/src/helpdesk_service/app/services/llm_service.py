"""
LLM Service — Azure OpenAI integration for answer generation and soft classification.
"""

import os
import logging
from typing import List, Optional

from openai import AzureOpenAI

from app.prompt import SYSTEM_PROMPT_ANSWER, SYSTEM_PROMPT_CLASSIFY, SYSTEM_PROMPT_ANALYZE_TICKET

logger = logging.getLogger(__name__)

# Initialize Azure OpenAI client
_client: Optional[AzureOpenAI] = None


def _get_client() -> AzureOpenAI:
    """Lazy-load the Azure OpenAI client."""
    global _client
    if _client is None:
        _client = AzureOpenAI(
            azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
            api_key=os.environ["AZURE_OPENAI_API_KEY"],
            api_version=os.environ.get("AZURE_OPENAI_API_VERSION", "2025-01-01-preview"),
        )
        logger.info("Azure OpenAI client initialized.")
    return _client


def _get_deployment() -> str:
    return os.environ.get("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o-aiforhr")


def generate_answer(query: str, kb_results: List[dict]) -> str:
    """
    Generate an LLM answer using retrieved KB articles as context.

    Args:
        query: The user's question.
        kb_results: List of dicts from retrieval_service.search_similar().

    Returns:
        LLM-generated answer string.
    """
    if not kb_results:
        context_block = "No relevant knowledge base articles were found."
    else:
        context_parts = []
        for i, r in enumerate(kb_results, 1):
            context_parts.append(
                f"--- Article {i} (similarity: {r['similarity']}) ---\n"
                f"Title: {r['title']}\n"
                f"Category: {r.get('category_name', 'N/A')}\n"
                f"Problem: {r['problem_description']}\n"
                f"Solution: {r['solution_steps']}\n"
            )
        context_block = "\n".join(context_parts)

    user_message = (
        f"User Query: {query}\n\n"
        f"Retrieved Knowledge Base Articles:\n{context_block}"
    )

    client = _get_client()
    response = client.chat.completions.create(
        model=_get_deployment(),
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT_ANSWER},
            {"role": "user", "content": user_message},
        ],
        temperature=0.3,
        max_tokens=1024,
    )

    answer = response.choices[0].message.content.strip()
    logger.info(f"LLM answer generated for query: '{query[:50]}...'")
    return answer


def classify_query(query: str) -> dict:
    """
    Use LLM to soft-classify a user query into a category and sub-category.
    Returns dict with 'category' and 'sub_category' keys (may be None).
    """
    client = _get_client()
    response = client.chat.completions.create(
        model=_get_deployment(),
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT_CLASSIFY},
            {"role": "user", "content": query},
        ],
        temperature=0.0,
        max_tokens=100,
    )

    raw = response.choices[0].message.content.strip()
    logger.info(f"LLM classification for '{query[:50]}...': {raw}")

    # Parse "Category: X | SubCategory: Y" format
    result = {"category": None, "sub_category": None}
    try:
        for part in raw.split("|"):
            part = part.strip()
            if part.lower().startswith("category:"):
                val = part.split(":", 1)[1].strip()
                if val.lower() not in ("none", "n/a", ""):
                    result["category"] = val
            elif part.lower().startswith("subcategory:"):
                val = part.split(":", 1)[1].strip()
                if val.lower() not in ("none", "n/a", ""):
                    result["sub_category"] = val
    except Exception:
        logger.warning(f"Failed to parse classification: {raw}")

    return result


def analyze_ticket(title: str, description: str) -> dict:
    """
    Use LLM to determine if a ticket needs approval and identify the approver.
    Returns dict with 'needs_approval' (bool) and 'approver_type' (str).
    """
    client = _get_client()
    user_content = f"Title: {title}\nDescription: {description}"
    response = client.chat.completions.create(
        model=_get_deployment(),
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT_ANALYZE_TICKET},
            {"role": "user", "content": user_content},
        ],
        temperature=0.0,
        max_tokens=100,
    )

    raw = response.choices[0].message.content.strip()
    logger.info(f"LLM analysis for ticket: {raw}")

    result = {"needs_approval": False, "approver_type": "None"}
    try:
        for part in raw.split("|"):
            part = part.strip()
            if part.lower().startswith("needsapproval:"):
                val = part.split(":", 1)[1].strip()
                result["needs_approval"] = val.lower() == "true"
            elif part.lower().startswith("approver:"):
                val = part.split(":", 1)[1].strip()
                result["approver_type"] = val
    except Exception:
        logger.warning(f"Failed to parse ticket analysis: {raw}")

    return result
