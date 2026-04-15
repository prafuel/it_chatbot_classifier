import uuid
import traceback
from pathlib import Path
from urllib.parse import urlparse
from fastapi import APIRouter, Depends, Request, HTTPException, Query, status

from app import schema
from app.common import api_logging
from app.common.auth import JWTBearer
from app.common.config import settings
from app.common.messages import LogMessages as Msg
from app.common.constant import (
    FILE_EXTRACTED_SITEMAPS, DIR_EXTRACTED_URLS, DIR_URL_CONTENT,
    FILE_CSV, SUFFIX_GRAPH_PKL, SUFFIX_TREE_JSON, SUFFIX_FLAT_JSON
)
from app.common.database import get_db
from app.common.crud import (
    create_chat,
    get_all_chats,
    get_chats_grouped_by_ip,
    get_chat_by_id,
    get_filterable_columns,
    get_distinct_column_values,
    get_chats_by_filter,
    get_chats_by_filters,
    get_grouped_chats_by_filters,
)

from app.utils.bot_utils.chatbot import chatbot
from app.utils.request_contrains.rate_limiter import allow_request
from app.utils.knowledge_tree.run import fetch_from_web, build_tree


logger = api_logging.logger
router = APIRouter()

@router.post("/query", response_model=schema.ChatbotResponse, status_code=status.HTTP_200_OK)
async def submit_query(request: Request, body: schema.ChatbotRequest):
    """
    Process user query through the Knowledge Graph and LLM pipeline.
    
    - Extracts context from FAISS Vector search and Graph expansion.
    - Re-ranks context with a CrossEncoder.
    - Prompts the LLM with the context to generate an answer.
    """
    
    user_data = body.user_data
    
    ip = user_data.ip
    logger.info(f"ip : {ip}")
    allow_user, cooldown_time = allow_request(ip)
    if not allow_user:
        return schema.ChatbotResponse(response=Msg.RATE_LIMIT_RESPONSE.format(cooldown_time))
    
    try:
        # Retrieve the pre-loaded models from application state
        graph = getattr(request.app.state, "graph", None)
        model = getattr(request.app.state, "embedding_model", None)
        index = getattr(request.app.state, "index", None)
        node_ids = getattr(request.app.state, "node_ids", None)
        node_payloads = getattr(request.app.state, "node_payloads", None)
        reranker = getattr(request.app.state, "reranker", None)
        
        if not all([graph, model, index, node_ids, reranker]) or node_payloads is None:
            logger.error(Msg.MODELS_NOT_LOADED)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=Msg.MODELS_UNAVAILABLE_DETAIL
            )
            
        logger.info(Msg.RECEIVED_QUERY.format(body.query))
        
        # Execute the core chatbot pipeline mapping from app.chatbot
        answer = chatbot(
            query=body.query,
            graph=graph,
            model=model,
            index=index,
            node_ids=node_ids,
            node_payloads=node_payloads,
            reranker=reranker
        )

        # ---- Persist to DB (non-fatal) ----
        try:
            loc  = user_data.location or {}
            net  = user_data.network or {}
            coords = getattr(loc, "coordinates", None) or {}

            db = get_db()
            create_chat(db, {
                "ip":           user_data.ip,
                "country":      getattr(loc, "country",     None),
                "country_code": getattr(loc, "countryCode", None),
                "region":       getattr(loc, "region",      None),
                "region_code":  getattr(loc, "regionCode",  None),
                "city":         getattr(loc, "city",        None),
                "zip":          getattr(loc, "zip",         None),
                "lat":          coords.get("lat") if isinstance(coords, dict) else None,
                "lon":          coords.get("lon") if isinstance(coords, dict) else None,
                "timezone":     getattr(loc, "timezone",    None),
                "isp":          getattr(net, "isp",          None),
                "organization": getattr(net, "organization", None),
                "asn":          getattr(net, "asn",          None),
                "query":        body.query,
                "response":     answer,
            })
        except Exception as db_err:
            logger.error(f"DB save failed (non-fatal): {db_err}")

        return schema.ChatbotResponse(
            response=answer
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(Msg.QUERY_HANDLING_ERROR.format(body.query, str(e)))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=Msg.QUERY_RESPONSE_FAILED
        )

@router.post("/build", response_model=schema.BuildResponse, status_code=status.HTTP_200_OK)
async def build_knowledge_graph(request: Request, body: schema.BuildRequest):
    """
    Orchestrate data collection and knowledge graph creation for a given URL.
    
    1. Crawls the sitemaps to get URLs.
    2. Collects text data from URLs and saves to CSV.
    3. Builds the knowledge graph from the CSV and saves as .pkl.
    """
    try:
        url = body.url.strip()
        if not url:
            raise HTTPException(status_code=400, detail=Msg.URL_EMPTY_DETAIL)

        # Parse url to find website name
        parsed = urlparse(url)
        domain = parsed.netloc or url
        website_name = domain.replace("www.", "")

        # Resolve base directory safely — works both locally and in Docker
        base_dir = Path(__file__).resolve().parents[4]  # /app inside Docker

        data_dir = base_dir / "data" / website_name
        data_dir.mkdir(parents=True, exist_ok=True)

        final_data_dir = base_dir / "data"
        final_data_dir.mkdir(parents=True, exist_ok=True)

        # File paths for WebExtraction
        extracted_sitemaps = data_dir / FILE_EXTRACTED_SITEMAPS
        extracted_urls_dir = data_dir / DIR_EXTRACTED_URLS
        url_content_dir = data_dir / DIR_URL_CONTENT
        csv_file = data_dir / FILE_CSV
        
        final_graph_file = final_data_dir / f"{website_name}{SUFFIX_GRAPH_PKL}"
        final_tree_file  = final_data_dir / f"{website_name}{SUFFIX_TREE_JSON}"
        final_flat_file  = final_data_dir / f"{website_name}{SUFFIX_FLAT_JSON}"
                
        logger.info(Msg.BUILD_STARTED.format(url, website_name))
        
        # 1. Web Extraction (Crawling + Content fetching)
        logger.info(Msg.EXTRACTING_WEB_CONTENT.format(url))
        fetch_from_web(schema.WebExtractionSchema(
            url=str(url),
            extracted_sitemap_urls=str(extracted_sitemaps),
            extracted_urls=str(extracted_urls_dir),
            urls_content=str(url_content_dir)
        ))

        # 2. Knowledge Graph Building
        logger.info(Msg.BUILDING_KG_MODELS)
        build_tree(schema.GraphBotSchema(
            urls_content=str(url_content_dir),
            csv_output=str(csv_file),
            output_pkl=str(final_graph_file),
            output_tree=str(final_tree_file),
            output_flat=str(final_flat_file)
        ))

        logger.info(Msg.GRAPH_BUILT_SUCCESS.format(final_graph_file))

        return schema.BuildResponse(
            message=Msg.BUILD_SUCCESS_MSG.format(website_name),
            intermediate_folder=str(data_dir),
            final_output_file=str(final_graph_file)
        )
    except Exception as e:
        err_msg = traceback.format_exc()
        logger.error(Msg.BUILD_KG_ERROR.format(body.url, err_msg))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=Msg.BUILD_KG_FAILED.format(str(e))
        )


# ---------------------------------------------------------------------------
# Chat history endpoints  (all require admin JWT)
# ---------------------------------------------------------------------------

@router.get(
    "/chats",
    response_model=list[schema.ChatSessionResponse],
    status_code=status.HTTP_200_OK,
    summary="Get all chat sessions",
    dependencies=[Depends(JWTBearer())],
)
async def get_chats(
    page: int = Query(1, ge=1, description="Page number to retrieve"),
):
    """
    Return a paginated list of all stored chat sessions, newest first.
    Uses BATCH_SIZE from configuration.
    Requires admin JWT.
    """
    db = get_db()
    chats, _ = get_chats_grouped_by_ip(db, page=page, batch_size=settings.BATCH_SIZE)
    return chats


# ---- Column-based filter endpoints (dropdown support) ----

@router.get(
    "/chats/columns",
    response_model=schema.FilterableColumnsResponse,
    status_code=status.HTTP_200_OK,
    summary="List filterable columns",
    dependencies=[Depends(JWTBearer())],
)
async def list_filterable_columns():
    """
    Return the column names that can be used for filtering chat sessions.
    Use this to populate a "select column" dropdown.
    Requires admin JWT.
    """
    return schema.FilterableColumnsResponse(columns=get_filterable_columns())


@router.get(
    "/chats/columns/{column_name}/values",
    response_model=schema.ColumnValuesResponse,
    status_code=status.HTTP_200_OK,
    summary="Get distinct values for a column",
    dependencies=[Depends(JWTBearer())],
)
async def list_column_values(column_name: str):
    """
    Return all distinct non-null values stored in the given column.
    Use this to populate a "select value" dropdown after a column is chosen.
    Requires admin JWT.
    """
    try:
        db = get_db()
        values = get_distinct_column_values(db, column_name)
        return schema.ColumnValuesResponse(column=column_name, values=values)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post(
    "/chats/filter",
    response_model=schema.FilteredChatsResponse,
    status_code=status.HTTP_200_OK,
    summary="Filter chats by one or more column values",
    dependencies=[Depends(JWTBearer())],
)
async def filter_chats(body: schema.ChatsFilterRequest):
    """
    Return chat sessions matching ALL key/value pairs in the request body, with optional sorting.

    **Request body** example:
    ```json
    {"filters": {"city": "Pune", "country": "India"}, "sort_by": "created_at", "sort_type": "desc"}
    ```

    - String columns are matched case-insensitively (ILIKE).
    - Multiple filters are ANDed together.
    - An empty `filters` object returns all chats.
    - Raises 400 if any key is not a valid filterable column.
    - Requires admin JWT.
    """
    try:
        db = get_db()
        chats, total_ips = get_grouped_chats_by_filters(
            db, 
            body.filters, 
            sort_by=body.sort_by, 
            sort_type=body.sort_type
        )

        # total_count
        total_count = sum([len(chat.chats) for chat in chats])

        return schema.FilteredChatsResponse(chats=chats, total_count=total_count)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


# ---- Single chat by ID ----

@router.get(
    "/chats/{chat_id}",
    response_model=schema.ChatSessionResponse,
    status_code=status.HTTP_200_OK,
    summary="Get a chat session by ID",
    dependencies=[Depends(JWTBearer())],
)
async def get_chat(chat_id: uuid.UUID):
    """
    Return a single chat session by its UUID.
    Requires admin JWT.
    """
    db = get_db()
    chat = get_chat_by_id(db, chat_id)
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chat session {chat_id} not found",
        )
    return chat