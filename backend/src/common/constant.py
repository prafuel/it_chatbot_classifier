"""
Application constants for ACL Chatbot services.
Values are sourced from environment variables via config.settings.
"""

from app.common.config import settings

# JWT Configuration
JWT_SECRET_KEY = settings.jwt_secret_key
API_ALGORITHM = settings.algorithm
API_ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_token_expire_seconds // 60

# Encryption
ENCRYPTION_KEY = settings.ENCRYPTION_KEY

# Logging
LOG_LEVELS = ["INFO", "DEBUG", "ERROR"]

# Chatbot Configurations
ENRICHED_GRAPH_PATH  = "acldigital.com_knowledge_graph.pkl"
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
RERANKER_MODEL_NAME  = "cross-encoder/ms-marco-MiniLM-L-6-v2"
TOP_K_RETRIEVAL      = 15
TOP_K_FINAL          = 5
MAX_CONTEXT_PAGES    = 5
MAX_GRAPH_NEIGHBOURS = 2
INDEXABLE_NODE_TYPES = {"page", "section"}

# Web Extraction & Graph Building Defaults
DEFAULT_HEADERS = {'User-Agent': 'Mozilla/5.0'}
SITEMAP_INDEX_SUFFIX = "/sitemap_index.xml"
SITEMAP_SUFFIX = "/sitemap.xml"

# Default Output Paths for CLI testing
DEFAULT_SITE_URL = "https://www.acldigital.com/sitemap_index.xml"
DEFAULT_EXTRACTED_SITEMAP_URLS = "results/extracted_sitemap_urls.txt"
DEFAULT_EXTRACTED_URLS = "results/extracted_urls"
DEFAULT_URLS_CONTENT = "results/url_content"
DEFAULT_CSV_OUTPUT = "webcontent.csv"
DEFAULT_OUTPUT_PKL = "results/pickle/knowledge_graph.pkl"
DEFAULT_OUTPUT_TREE = "results/graph_json/knowledge_graph_tree.json"
DEFAULT_OUTPUT_FLAT = "results/graph_json/knowledge_graph_flat.json"

# API File Generation Constants
FILE_EXTRACTED_SITEMAPS = "extracted_sitemap_urls.txt"
DIR_EXTRACTED_URLS = "extracted_urls"
DIR_URL_CONTENT = "url_content"
FILE_CSV = "webcontent.csv"

SUFFIX_GRAPH_PKL = "_knowledge_graph.pkl"
SUFFIX_TREE_JSON = "_knowledge_graph_tree.json"
SUFFIX_FLAT_JSON = "_knowledge_graph_flat.json"

# Main App Default Paths
DEFAULT_KNOWLEDGE_GRAPH_PATH = "/app/data/knowledge_graph.pkl"
DEFAULT_FAISS_INDEX_PATH = "/app/data/faiss_index.bin"
DEFAULT_NODE_IDS_PATH = "/app/data/node_ids.pkl"

# Text Knowledge Base (Admin-uploaded extra content)
DEFAULT_TEXT_FAISS_INDEX_PATH = "/app/data/text_faiss_index.bin"
DEFAULT_TEXT_IDS_PATH = "/app/data/text_ids.pkl"
TEXT_CHUNK_SIZE = 100       # words per chunk
TEXT_CHUNK_OVERLAP = 20     # overlap in words
TOP_K_TEXT_RETRIEVAL = 2    # max results from text FAISS
