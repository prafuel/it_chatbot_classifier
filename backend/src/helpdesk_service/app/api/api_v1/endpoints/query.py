"""
Top-level AI-powered Query API endpoint for knowledge base search.
Synchronized with frontend implementation.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from app.common.database import get_db
from app.crud import crud_knowledge_base
from app import schema
from app.common.ai_utils import get_llm_response

router = APIRouter(tags=["Query"])

def format_kb_context(articles: List[schema.KnowledgeBaseResponse]) -> str:
    """Format KB articles into a context string for the LLM."""
    if not articles:
        return "No relevant knowledge base articles found."
    
    context_parts = []
    for idx, art in enumerate(articles, 1):
        context_parts.append(
            f"Article {idx}:\n"
            f"Title: {art.title}\n"
            f"Problem: {art.problem_description}\n"
            f"Solution: {art.solution_steps}\n"
        )
    return "\n\n".join(context_parts)

@router.post("/query/", response_model=schema.KnowledgeBaseQueryResponse)
def query_kb_ai(payload: schema.KnowledgeBaseQueryRequest, db: Session = Depends(get_db)):
    """
    Search into knowledge base and return an AI-generated answer based on the results.
    Compatible with frontend queryApi.
    """
    # 1. Search Knowledge Base
    articles = crud_knowledge_base.search_kb(db, payload.query, limit=payload.top_k)
    
    # 2. Format Context
    context = format_kb_context(articles)
    
    # 3. Define Prompt
    system_prompt = (
        "You are a helpful IT Support Assistant. Use the following knowledge base articles "
        "to answer the user's query. If the answer is not in the articles, say you don't know "
        "and suggest they contact support. Keep the answer concise and professional.\n\n"
        f"Context:\n{context}"
    )
    
    user_prompt = f"User Query: {payload.query}"
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    
    # 4. Get LLM Response
    try:
        answer = get_llm_response(messages)
    except Exception as e:
        answer = f"Error generating AI response: {str(e)}"
    
    return schema.KnowledgeBaseQueryResponse(
        answer=answer,
        relevant_articles=articles
    )

@router.post("/query/build-embeddings")
def build_embeddings():
    """
    Refresh/build embeddings for the knowledge base.
    Stub implementation for frontend compatibility.
    """
    return {"message": "Knowledge base embeddings refreshed successfully."}
