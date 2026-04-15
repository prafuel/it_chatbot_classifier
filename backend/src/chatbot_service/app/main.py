import os
from fastapi import FastAPI
from contextlib import asynccontextmanager
from starlette.middleware.cors import CORSMiddleware

from app.api.api_v1.api import router as api_router

from app.utils.bot_utils.chatbot import (
    load_graph, 
    load_embedding_model, 
    load_reranker_model, 
    build_vector_index, 
    save_vector_index, 
    load_vector_index
)
from app.utils.bot_utils.text_knowledge import load_text_vector_index

from app.common import api_logging
from app.common.config import settings
from app.common.messages import LogMessages as Msg
from app.common.constant import (
    DEFAULT_KNOWLEDGE_GRAPH_PATH,
    DEFAULT_FAISS_INDEX_PATH,
    DEFAULT_NODE_IDS_PATH,
    DEFAULT_TEXT_FAISS_INDEX_PATH,
    DEFAULT_TEXT_IDS_PATH,
)
from app.common.database import Base, get_db_engine
from app.common import models  # noqa: F401 — registers ORM models with Base
 
logger = api_logging.logger

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan event to load heavy ML models, FAISS indexes, 
    and the Knowledge Graph into memory before serving requests.
    """
    logger.info(Msg.SERVICE_STARTING)
    try:
        # Initialise PostgreSQL tables
        try:
            engine = get_db_engine()
            Base.metadata.create_all(bind=engine)
            logger.info("Database tables created / verified")
        except Exception as db_err:
            logger.error(f"DB init failed (non-fatal): {db_err}")

        # Resolve path to the knowledge graph
        graph_path = os.getenv("KNOWLEDGE_GRAPH_PATH", DEFAULT_KNOWLEDGE_GRAPH_PATH)
        
        # Resolve paths for FAISS index and node IDs
        faiss_index_path = os.getenv("FAISS_INDEX_PATH", DEFAULT_FAISS_INDEX_PATH)
        node_ids_path = os.getenv("NODE_IDS_PATH", DEFAULT_NODE_IDS_PATH)
        
        app.state.graph = load_graph(graph_path)
        app.state.embedding_model = load_embedding_model()
        app.state.reranker = load_reranker_model()
        
        # Try to load existing FAISS index
        loaded = load_vector_index(faiss_index_path, node_ids_path)
        if loaded:
            app.state.index, app.state.node_ids, app.state.node_payloads = loaded
        else:
            logger.info(Msg.FAISS_INDEX_NOT_FOUND)
            app.state.index, app.state.node_ids, app.state.node_payloads = build_vector_index(app.state.graph, app.state.embedding_model)
            save_vector_index(app.state.index, app.state.node_ids, app.state.node_payloads, faiss_index_path, node_ids_path)
            
        # Try to load optional Admin Text Knowledge Base
        text_index_path = os.getenv("TEXT_FAISS_INDEX_PATH", DEFAULT_TEXT_FAISS_INDEX_PATH)
        text_ids_path = os.getenv("TEXT_IDS_PATH", DEFAULT_TEXT_IDS_PATH)
        text_loaded = load_text_vector_index(text_index_path, text_ids_path)
        if text_loaded:
            app.state.text_index, app.state.text_chunks = text_loaded
        else:
            logger.info(Msg.TEXT_INDEX_NOT_FOUND)
            app.state.text_index, app.state.text_chunks = None, None
        
        logger.info(Msg.ALL_MODELS_LOADED)
    except Exception as e:
        logger.error(Msg.COMPONENTS_LOAD_FAILED.format(e))
        # Allow the app to start but log heavily. API endpoints will fail gracefully if state is missing.
    
    yield
    
    # Cleanup on shutdown (if any is needed)
    logger.info(Msg.SERVICE_SHUTTING_DOWN)
    app.state.graph = None
    app.state.embedding_model = None
    app.state.reranker = None
    app.state.index = None
    app.state.node_ids = None
    app.state.node_payloads = None
    app.state.text_index = None
    app.state.text_chunks = None


app = FastAPI(
    title="ACL Chatbot Service",
    description="Knowledge Graph & AI-powered Chatbot backend API",
    version="1.0.0",
    lifespan=lifespan
)

# Set all CORS enabled origins
if settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.cors_origins.split(",")],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(api_router, prefix="/api/v1")