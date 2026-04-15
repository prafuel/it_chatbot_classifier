"""
Shared log message constants for all ACL Chatbot services.

Usage:
    from app.common.messages import LogMessages
"""


class LogMessages:
    """Log messages used by usermanagementservice and shared modules."""

    # User CRUD operations
    USER_CREATED_SUCCESS = "User created successfully: {}"
    USER_SAVE_FAILED = "Failed to save user: {}"
    USER_CREATION_ERROR = "Error creating user: {}"
    FETCH_USER_BY_ID_ERROR = "Error fetching user by ID: {}"
    FETCH_USER_BY_UUID_ERROR = "Error fetching user by UUID: {}"
    FETCH_USER_BY_EMAIL_ERROR = "Error fetching user by email: {}"
    AUTHENTICATION_ERROR = "Authentication error: {}"
    USER_DATA_DECRYPTION_ERROR = "Error decrypting user data: {}"

    # JSON Handler operations
    DIRECTORY_CREATED = "Directory created: {}"
    JSON_FILE_CREATED = "JSON file created: {}"
    JSON_DECODE_ERROR = "JSON decode error: {}"
    JSON_READ_ERROR = "JSON read error: {}"
    JSON_WRITE_ERROR = "JSON write error: {}"
    USER_ADDED = "User added to JSON storage: {}"
    USER_ADD_ERROR = "Error adding user to JSON storage: {}"
    GET_ALL_USERS_ERROR = "Error getting all users: {}"
    FIND_USER_ERROR = "Error finding user by {}: {}"
    TOKEN_BLACKLISTED = "Token blacklisted for user: {}"
    TOKEN_BLACKLIST_ERROR = "Error blacklisting token: {}"
    TOKEN_BLACKLIST_CHECK_ERROR = "Error checking token blacklist: {}"

    # Auth / Endpoint operations
    USER_SIGNUP_SUCCESS = "User signup successful: {}"
    SIGNUP_ERROR = "Signup error: {}"
    USER_LOGIN_SUCCESS = "User login successful: {}"
    LOGIN_ERROR = "Login error: {}"
    USER_LOGOUT_SUCCESS = "User logout successful: {}"
    LOGOUT_ERROR = "Logout error: {}"
    GET_CURRENT_USER_ERROR = "Error fetching current user: {}"

    # -----------------------------------------------------------------------
    # Chatbot Service — Model Loading
    # -----------------------------------------------------------------------
    GRAPH_LOADED = "Graph loaded — nodes: %d, edges: %d"
    GRAPH_LOAD_FAILED = "Failed to load graph from %s: %s"
    EMBEDDING_MODEL_LOADED = "Embedding model '%s' loaded"
    EMBEDDING_MODEL_LOAD_FAILED = "Failed to load embedding model '%s': %s"
    RERANKER_MODEL_LOADED = "Reranker model '%s' loaded"
    RERANKER_MODEL_LOAD_FAILED = "Failed to load reranker model '%s': %s"

    # Chatbot Service — Vector Index
    EMPTY_DOCUMENT_SET = "Empty document set; cannot build vector index"
    ENCODING_DOCUMENTS = "Encoding %d documents for FAISS index …"
    VECTOR_INDEX_BUILT = "Vector index built — %d pages indexed, embedding dim: %d"
    VECTOR_INDEX_BUILD_ERROR = "Error in build_vector_index: {}"
    VECTOR_INDEX_SAVED = "Vector index saved to %s and %s"
    VECTOR_INDEX_SAVE_FAILED = "Failed to save vector index: %s"
    VECTOR_INDEX_LOADED = "Vector index loaded from %s and %s"
    VECTOR_INDEX_LOAD_FAILED = "Failed to load vector index from %s or %s: %s"
    ADD_PAYLOAD_FILTER = "Extracted payload %s for URL: %s"

    # Chatbot Service — Intent & Search
    DETECTED_INTENT = "Detected intent: %s"
    INTENT_CLASSIFICATION_FAILED = "Intent classification failed: %s"
    SEARCH_RETRIEVED = "Search retrieved %d candidates (filtered to %d)"
    SEARCH_FAILED = "Search failed for query '%s': %s"

    # Chatbot Service — Graph Expansion & Reranking
    GRAPH_EXPANSION = "Graph expansion: %d seed → %d total pages"
    GRAPH_EXPANSION_ERROR = "Error in expand_graph: {}"
    RERANKED_PAGES = "Reranked %d pages down to top %d"
    RERANKING_FAILED = "Reranking failed: %s"

    # Chatbot Service — Context & Answer Generation
    CONTEXT_BUILT = "Context built from %d pages (base=%d, extra=%d)"
    CONTEXT_BUILD_ERROR = "Error in build_context: {}"
    LLM_RESPONSE_FAILED = "LLM response generation failed: %s"
    LLM_FALLBACK_RESPONSE = "I'm sorry, I encountered an error generating a response."

    # Chatbot Service — Pipeline
    INITIAL_SEARCH_CANDIDATES = "Initial search candidates: %s"
    EXPANDED_CANDIDATE_NODES = "Expanded candidate nodes: %s"
    TOP_NODES_AFTER_RERANKING = "Top nodes after reranking: %s"
    CHATBOT_PIPELINE_ERROR = "Error in chatbot pipeline: {}"
    CHATBOT_INITIALIZING = "Initializing ACL Website Chatbot..."
    CHATBOT_RUN_ERROR = "Error in run_chatbot: {}"

    # Chatbot Service — CLI
    CLI_BANNER_LINE = "=" * 55
    CLI_TITLE = "  ACL Digital Website Chatbot"
    CLI_INSTRUCTIONS = "  Type your question, or 'exit' / 'quit' to stop."
    CLI_GOODBYE = "Goodbye!"

    # Chatbot Service — Main / Lifespan
    SERVICE_STARTING = "Starting Chatbot Service — Loading models and graphs..."
    FAISS_INDEX_NOT_FOUND = "FAISS index not found or failed to load. Building new index..."
    ALL_MODELS_LOADED = "All Chatbot models and graphs loaded successfully into app.state."
    COMPONENTS_LOAD_FAILED = "Failed to load required Chatbot components: {}"
    SERVICE_SHUTTING_DOWN = "Shutting down Chatbot Service..."

    # Chatbot Service — API
    RATE_LIMIT_RESPONSE = "too much requests, cooldown for {}"
    MODELS_NOT_LOADED = "API called, but Chatbot models were not loaded properly during startup."
    MODELS_UNAVAILABLE_DETAIL = "Chatbot AI models are currently unavailable. Please try again later."
    RECEIVED_QUERY = "Received chatbot query: '{}'"
    QUERY_HANDLING_ERROR = "Error handling query '{}': {}"
    QUERY_RESPONSE_FAILED = "Failed to generate response for the given query."
    URL_EMPTY_DETAIL = "URL cannot be empty."
    BUILD_STARTED = "Starting build process for URL: {} -> {}"
    EXTRACTING_WEB_CONTENT = "Extracting web content from {}..."
    BUILDING_KG_MODELS = "Building knowledge graph models and outputs..."
    GRAPH_BUILT_SUCCESS = "Graph successfully built at {}"
    BUILD_SUCCESS_MSG = "Successfully built knowledge graph for {}."
    BUILD_KG_ERROR = "Error building knowledge graph for '{}': {}"
    BUILD_KG_FAILED = "Failed to build knowledge graph: {}"

    # Chatbot Service — Web Extraction
    FETCH_XML_FAILED = "Failed to fetch XML: {} | Status: {}"
    GET_XML_ERROR = "Error in get_xml for {}: {}"
    USING_SITEMAP = "[INFO] Using sitemap: {}"
    NO_VALID_SITEMAP = "No valid sitemap found (tried sitemap_index.xml and sitemap.xml)"
    RESOLVE_SITEMAP_ERROR = "Error in resolve_sitemap: {}"
    GET_WEBCONTENT_ERROR = "Error in get_webcontent for {}: {}"
    NO_LOC_TAGS = "No <loc> tags found in sitemap"
    GET_ALL_SITEURLS_ERROR = "Error in get_all_siteurls: {}"
    USING_DIRECT_URL_LIST = "[INFO] Using direct URL list (no sitemap index)"
    URL_CRAWL_ERROR = "Error in url_crawl: {}"
    FETCH_URL_FAILED = "[ERROR] Failed to fetch {}: {}"
    CONTENT_EXTRACTION_ERROR = "Error in content_extraction: {}"

    # Chatbot Service — Creating Knowledge Bot
    SAFE_ERROR = "Error in safe: {}"
    TO_CSV_ERROR = "Error in to_csv: {}"
    TO_PICKLE_ERROR = "Error in to_pickle: {}"
    BUILD_TREE_ERROR = "Error in build_tree: {}"
    LOADING_PICKLE = "Loading pickle …"
    TREE_JSON_SAVED = "Tree JSON saved  → {}"
    TO_JSON_ERROR = "Error in to_json: {}"

    # Chatbot Service — Service / Rate Limiting
    ALLOW_REQUEST_ERROR = "Error in allow_request: {}"

    # Chatbot Service — Text Knowledge Base (Admin extra content)
    TEXT_EMPTY_DETAIL = "Text content cannot be empty."
    TEXT_CHUNKED = "Text chunked into %d pieces (chunk_size=%d, overlap=%d)"
    TEXT_INDEX_BUILT = "Text FAISS index built — %d chunks indexed, dim=%d"
    TEXT_INDEX_BUILD_ERROR = "Error building text vector index: {}"
    TEXT_INDEX_SAVED = "Text FAISS index saved to %s and %s"
    TEXT_INDEX_SAVE_FAILED = "Failed to save text FAISS index: %s"
    TEXT_INDEX_LOADED = "Text FAISS index loaded from %s and %s"
    TEXT_INDEX_LOAD_FAILED = "Failed to load text FAISS index from %s or %s: %s"
    TEXT_INDEX_NOT_FOUND = "Text FAISS index not found on disk — will be created when admin uploads text."
    TEXT_SEARCH_RESULTS = "Text FAISS search returned %d results"
    TEXT_SEARCH_FAILED = "Text FAISS search failed for query '%s': %s"
    TEXT_INGEST_SUCCESS = "Admin text ingested — %d chunks, index at %s"
    TEXT_INGEST_ERROR = "Error ingesting admin text: {}"
    TEXT_CONTEXT_APPENDED = "Appended %d text knowledge snippets to LLM context"