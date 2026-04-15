import os
import logging
import pickle

import faiss
import numpy as np
import networkx as nx
from sentence_transformers import SentenceTransformer, CrossEncoder

from app.common.ai_utils import get_llm_response
from app.common.messages import LogMessages as Msg
from app.prompt import INTENT_PROMPT, BOT_SYSTEM_PROMPT
from app.utils.bot_utils.text_knowledge import search_text_index

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
from app.common.constant import (
    ENRICHED_GRAPH_PATH,
    EMBEDDING_MODEL_NAME,
    RERANKER_MODEL_NAME,
    TOP_K_RETRIEVAL,
    TOP_K_FINAL,
    MAX_CONTEXT_PAGES,
    MAX_GRAPH_NEIGHBOURS,
    INDEXABLE_NODE_TYPES
)

# ---------------------------------------------------------------------------
# Logger setup
# ---------------------------------------------------------------------------
# Removed basicConfig to allow unified logging via Loguru interceptor
logger = logging.getLogger(__name__)


# ===========================================================================
# 1. Load component models
# ===========================================================================
def load_graph(path: str = ENRICHED_GRAPH_PATH) -> nx.DiGraph:
    """Load the enriched knowledge graph from a pickle file."""
    try:
        with open(path, "rb") as fh:
            graph = pickle.load(fh)
        logger.info(
            Msg.GRAPH_LOADED,
            graph.number_of_nodes(),
            graph.number_of_edges(),
        )
        return graph
    except (OSError, pickle.UnpicklingError) as exc:
        logger.error(Msg.GRAPH_LOAD_FAILED, path, exc)
        raise

def load_embedding_model(model_name: str = EMBEDDING_MODEL_NAME) -> SentenceTransformer:
    """Load the sentence-transformer model."""
    try:
        model = SentenceTransformer(model_name)
        logger.info(Msg.EMBEDDING_MODEL_LOADED, model_name)
        return model
    except Exception as exc:
        logger.error(Msg.EMBEDDING_MODEL_LOAD_FAILED, model_name, exc)
        raise

def load_reranker_model(model_name: str = RERANKER_MODEL_NAME) -> CrossEncoder:
    """Load the cross-encoder model for reranking search results."""
    try:
        model = CrossEncoder(model_name)
        logger.info(Msg.RERANKER_MODEL_LOADED, model_name)
        return model
    except Exception as exc:
        logger.error(Msg.RERANKER_MODEL_LOAD_FAILED, model_name, exc)
        raise


# ===========================================================================
# 2. Build FAISS vector index from node content
# ===========================================================================
from urllib.parse import urlparse

def build_vector_index(
    graph: nx.DiGraph,
    model: SentenceTransformer,
) -> tuple[faiss.IndexFlatL2, list[str], list[dict]]:
    """Build a fast vector index over label + content."""
    try:
        documents: list[str] = []
        node_ids: list[str] = []
        node_payloads: list[dict] = []

        for node_id, data in graph.nodes(data=True):
            if data.get("node_type") not in INDEXABLE_NODE_TYPES:
                continue

            content = data.get("content", "").strip()
            if not content:
                continue

            label = data.get("label", "")
            text = f"{label}. {content}"

            documents.append(text)
            node_ids.append(node_id)

            # Implement proposed Key-Value Payload extraction for filters
            payload = {}
            full_url = data.get("full_url", "")
            if full_url:
                parsed = urlparse(full_url)
                path = parsed.path.strip('/')
                parts = [p.lower() for p in path.split('/') if p]

                if parts:
                    root_section = parts[0]
                    # Restrict payload enforcement to our targeted filtered sections
                    if root_section in ["offerings", "industries", "solutions"]:
                        key = root_section
                        value = parts[-1] if len(parts) > 0 else root_section
                        payload = {key: value}
            
            if payload:
                # logger.info("Extracted payload %s for URL: %s", payload, full_url) ADD_PAYLOAD_FILTER
                logger.info(Msg.ADD_PAYLOAD_FILTER, payload, full_url)
            node_payloads.append(payload)

        if not documents:
            raise ValueError(Msg.EMPTY_DOCUMENT_SET)

        logger.info(Msg.ENCODING_DOCUMENTS, len(documents))
        embeddings = model.encode(documents, show_progress_bar=True, batch_size=64)
        embeddings = np.array(embeddings, dtype=np.float32)

        dim = embeddings.shape[1]
        index = faiss.IndexFlatL2(dim)
        index.add(embeddings)

        logger.info(Msg.VECTOR_INDEX_BUILT, len(documents), dim)
        return index, node_ids, node_payloads
    except Exception as e:
        logger.error(Msg.VECTOR_INDEX_BUILD_ERROR.format(e))
        raise

def save_vector_index(
    index: faiss.IndexFlatL2,
    node_ids: list[str],
    node_payloads: list[dict],
    index_path: str,
    ids_path: str
) -> None:
    """Save the FAISS index and node IDs to disk."""
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(os.path.abspath(index_path)), exist_ok=True)
        os.makedirs(os.path.dirname(os.path.abspath(ids_path)), exist_ok=True)

        faiss.write_index(index, index_path)
        with open(ids_path, "wb") as fh:
            # Saving both node_ids and their respective metadata payloads
            pickle.dump((node_ids, node_payloads), fh)
        logger.info(Msg.VECTOR_INDEX_SAVED, index_path, ids_path)
    except Exception as exc:
        logger.error(Msg.VECTOR_INDEX_SAVE_FAILED, exc)


def load_vector_index(
    index_path: str,
    ids_path: str
) -> tuple[faiss.IndexFlatL2, list[str], list[dict]] | None:
    """Load the FAISS index and node IDs from disk."""
    if not os.path.exists(index_path) or not os.path.exists(ids_path):
        return None

    try:
        index = faiss.read_index(index_path)
        with open(ids_path, "rb") as fh:
            data = pickle.load(fh)
            # Support backwards compatibility if pickle only has node_ids
            if isinstance(data, tuple) and len(data) == 2:
                node_ids, node_payloads = data
            else:
                node_ids = data
                node_payloads = [{}] * len(node_ids)

        logger.info(Msg.VECTOR_INDEX_LOADED, index_path, ids_path)
        return index, node_ids, node_payloads
    except Exception as exc:
        logger.error(Msg.VECTOR_INDEX_LOAD_FAILED, index_path, ids_path, exc)
        return None
    
# ===========================================================================
# 3. Intent Classification (LLM-based)
# ===========================================================================
def classify_intent(query: str) -> str:
    """Classify user query into one of predefined intents to restrict search space."""
    prompt = (query)
    try:
        raw_resp = get_llm_response(prompt)
        intent = raw_resp.strip().upper()
        
        valid_intents = {"CAREERS", "CONTACT", "PARTNERS", "ABOUT", "SERVICES", "INDUSTRIES", "GENERAL"}
        
        for v in valid_intents:
            if v in intent:
                intent = v
                break
                
        if intent not in valid_intents:
            intent = "GENERAL"
            
        logger.info(Msg.DETECTED_INTENT, intent)
        return intent
    except Exception as exc:
        logger.error(Msg.INTENT_CLASSIFICATION_FAILED, exc)
        return "GENERAL"


# ===========================================================================
# 4. Search and Filter Pages
# ===========================================================================
def search_pages(
    query: str,
    intent: str,
    graph: nx.DiGraph,
    model: SentenceTransformer,
    index: faiss.IndexFlatL2,
    node_ids: list[str],
    top_k: int = TOP_K_RETRIEVAL,
) -> list[str]:
    """Retrieve top-K pages, with optional filtering based on detected intent."""
    try:
        query_embedding = model.encode([query])
        query_embedding = np.array(query_embedding, dtype=np.float32)

        distances, indices = index.search(query_embedding, top_k)
        candidates = [node_ids[i] for i in indices[0] if 0 <= i < len(node_ids)]
        
        # Intent-based filtering
        filtered_candidates = []
        for node in candidates:
            data = graph.nodes.get(node, {})
            url = data.get("full_url", "").lower()
            label = data.get("label", "").lower()
            content = data.get("content", "").lower()
            
            combined_text = f"{url} {label} {content}"
            
            keep = False
            if intent == "CAREERS" and any(w in combined_text for w in ["career", "job", "hir"]):
                keep = True
            elif intent == "CONTACT" and "contact" in combined_text:
                keep = True
            elif intent == "PARTNERS" and ("partner" in combined_text or "alliance" in combined_text):
                keep = True
            elif intent == "ABOUT" and "about" in combined_text:
                keep = True
            elif intent in ("SERVICES", "INDUSTRIES", "GENERAL"):
                keep = True # Don't aggressively filter broad intents
                
            if keep:
                filtered_candidates.append(node)

        # Fallback to general search if the filter was too strict
        final_candidates = filtered_candidates if filtered_candidates else candidates
        
        logger.info(Msg.SEARCH_RETRIEVED, len(candidates), len(final_candidates))
        return final_candidates

    except Exception as exc:
        logger.error(Msg.SEARCH_FAILED, query, exc)
        return []


# ===========================================================================
# 5. Bounded Graph Expansion
# ===========================================================================
def expand_graph(graph: nx.DiGraph, nodes: list[str], max_neighbours: int = MAX_GRAPH_NEIGHBOURS) -> list[str]:
    """
    Expand the result set to include direct neighbours, bounded to prevent bloat.
    We only include neighbours if they are page or section nodes.
    """
    try:
        expanded: dict[str, int] = {n: 0 for n in nodes}   # seed nodes get priority 0

        for node in nodes:
            if node not in graph:
                continue
                
            try:
                # We use out_edges like the current base
                out_edges = list(graph.out_edges(node, data=True))
                added_count = 0
                for _, neighbour, edge_data in out_edges:
                    if added_count >= max_neighbours:
                        break
                    if neighbour in expanded:
                        continue
                    ntype = graph.nodes[neighbour].get("node_type", "")
                    if ntype in INDEXABLE_NODE_TYPES:
                        expanded[neighbour] = 1
                        added_count += 1
            except nx.NetworkXError:
                continue

        # Return seeds first, then expansions
        result = sorted(expanded.keys(), key=lambda n: expanded[n])
        logger.info(Msg.GRAPH_EXPANSION, len(nodes), len(result))
        return result
    except Exception as e:
        logger.error(Msg.GRAPH_EXPANSION_ERROR.format(e))
        return nodes


# ===========================================================================
# 6. Cross-Encoder Reranking
# ===========================================================================
def rerank_results(
    query: str,
    nodes: list[str],
    graph: nx.DiGraph,
    reranker: CrossEncoder,
    top_k: int = TOP_K_FINAL
) -> list[str]:
    """Score the expanded nodes precisely against the specific query using a cross-encoder."""
    if not nodes:
        return []
        
    pairs = []
    for node in nodes:
        data = graph.nodes.get(node, {})
        label = data.get("label", "")
        content = data.get("content", "")
        # The text block the reranker will evaluate
        text = f"{label}. {content[:1000]}" # limit content length for reranker
        pairs.append([query, text])
        
    try:
        scores = reranker.predict(pairs)
        
        # Sort nodes by score descending
        scored_nodes = list(zip(scores, nodes))
        scored_nodes.sort(key=lambda x: x[0], reverse=True)
        
        reranked_nodes = [node for score, node in scored_nodes[:top_k]]
        logger.info(Msg.RERANKED_PAGES, len(nodes), len(reranked_nodes))
        return reranked_nodes
    except Exception as exc:
        logger.error(Msg.RERANKING_FAILED, exc)
        return nodes[:top_k]

def build_context(
    graph: nx.DiGraph,
    nodes: list[str],
    max_pages: int = MAX_CONTEXT_PAGES
) -> str:
    """Assemble a textual context block with URL mismatch handling."""
    try:
        context_parts: list[str] = []
        used_urls = set()
        extra_slots = 0  # dynamic increase

        def normalize_url(node_id: str) -> str:
            """Construct URL from node_id."""
            return f"https://{node_id}"

        i = 0
        total_allowed = max_pages

        while i < len(nodes) and len(context_parts) < total_allowed + extra_slots:
            node_id = nodes[i]
            data = graph.nodes.get(node_id, {})

            label   = data.get("label", node_id.split("/")[-1])
            section = data.get("section", "unknown")
            full_url = data.get("full_url")
            node_url = normalize_url(node_id)

            content = data.get("content", "No content available.")

            # Truncate content
            content_snippet = content[:800].strip()
            if len(content) > 800:
                content_snippet += " …"

            urls_to_add = []

            # Case 1: full_url missing → fallback to node_url
            if not full_url:
                urls_to_add.append(node_url)

            # Case 2: mismatch → include BOTH
            elif full_url != node_url:
                urls_to_add.append(node_url)
                urls_to_add.append(full_url)
                extra_slots += 1  # allow one extra slot dynamically

            # Case 3: normal case
            else:
                urls_to_add.append(full_url)

            for url in urls_to_add:
                if url in used_urls:
                    continue  # avoid duplicates

                context_parts.append(
                    f"Page    : {label}  (section: {section})\n"
                    f"URL     : {url}\n"
                    f"Content : {content_snippet}\n"
                )
                used_urls.add(url)

                # Stop if we hit dynamic limit
                if len(context_parts) >= total_allowed + extra_slots:
                    break

            i += 1

        context = "\n---\n".join(context_parts)

        logger.info(
            Msg.CONTEXT_BUILT,
            len(context_parts),
            max_pages,
            extra_slots
        )

        return context
    except Exception as e:
        logger.error(Msg.CONTEXT_BUILD_ERROR.format(e))
        return ""

# ===========================================================================
# 8. Generate answer
# ===========================================================================
def generate_answer(query: str, context: str) -> str:
    """Send the user query + page context to the LLM and return the answer."""
    prompt = BOT_SYSTEM_PROMPT.format(query=query, context=context)

    try:
        answer = get_llm_response(prompt)
        return answer
    except Exception as exc:
        logger.error(Msg.LLM_RESPONSE_FAILED, exc)
        return Msg.LLM_FALLBACK_RESPONSE


# ===========================================================================
# 9. Main Pipeline
# ===========================================================================
def chatbot(
    query: str,
    graph: nx.DiGraph,
    model: SentenceTransformer,
    index: faiss.IndexFlatL2,
    node_ids: list[str],
    node_payloads: list[dict],
    reranker: CrossEncoder,
    text_index: faiss.IndexFlatL2 | None = None,
    text_chunks: list[str] | None = None,
) -> str:
    """End-to-end chatbot pipeline with Intent Classification and Reranking.
    
    *text_index* and *text_chunks* are optional.  When both are None the
    pipeline behaves exactly as the original graph-only flow.
    """
    try:
        # 1. Intent Classification
        intent = classify_intent(query)
        
        # 2. Vector search (filtered by intent)
        # Note: In a robust DB like Qdrant, we'd pass JSON filter dicts directly here mapping to `node_payloads`.
        # With FAISS, your colleague's Query-Rewriter component will apply the filter directly during this step. 
        candidates = search_pages(query, intent, graph, model, index, node_ids)
        logger.info(Msg.INITIAL_SEARCH_CANDIDATES, candidates)

        # 3. Bounded Graph expansion
        expanded_nodes = expand_graph(graph, candidates)
        logger.info(Msg.EXPANDED_CANDIDATE_NODES, expanded_nodes)

        # 4. Cross-Encoder reranking
        top_nodes = rerank_results(query, expanded_nodes, graph, reranker)
        logger.info(Msg.TOP_NODES_AFTER_RERANKING, top_nodes)

        # 5. Build context from graph
        context = build_context(graph, top_nodes)

        # 5b. (Optional) Append text knowledge base results
        if text_index is not None and text_chunks is not None:
            text_results = search_text_index(query, model, text_index, text_chunks)
            if text_results:
                text_context = "\n---\n".join(
                    f"Extra Info : {snippet}" for snippet in text_results
                )
                context = f"{context}\n\n--- Additional Knowledge Base ---\n{text_context}"
                logger.info(Msg.TEXT_CONTEXT_APPENDED, len(text_results))
        
        logger.info(f"Final Context for LLM:\n{context}\n")

        # 6. Generate LLM answer
        answer = generate_answer(query, context)

        return answer
    except Exception as e:
        logger.error(Msg.CHATBOT_PIPELINE_ERROR.format(e))
        return Msg.LLM_FALLBACK_RESPONSE


# ===========================================================================
# 10. CLI Loop
# ===========================================================================
def run_chatbot() -> None:
    """Initialise all components and start the interactive chatbot loop."""
    try:
        logger.info(Msg.CHATBOT_INITIALIZING)
        graph = load_graph()
        model = load_embedding_model()
        reranker = load_reranker_model()
        index, node_ids, node_payloads = build_vector_index(graph, model)

        print("\n" + Msg.CLI_BANNER_LINE)
        print(Msg.CLI_TITLE)
        print(Msg.CLI_INSTRUCTIONS)
        print(Msg.CLI_BANNER_LINE + "\n")

        while True:
            try:
                query = input("You: ").strip()
            except (EOFError, KeyboardInterrupt):
                print(f"\n{Msg.CLI_GOODBYE}")
                break

            if not query:
                continue

            if query.lower() in ("exit", "quit"):
                print(Msg.CLI_GOODBYE)
                break

            response = chatbot(query, graph, model, index, node_ids, node_payloads, reranker)
            print(f"\nBot: {response}\n")
    except Exception as e:
        logger.error(Msg.CHATBOT_RUN_ERROR.format(e))


if __name__ == "__main__":
    run_chatbot()