import os
import json
import pickle
import pandas as pd
import networkx as nx
from urllib.parse import urlparse
from collections import defaultdict

from app.common.messages import LogMessages as Msg
from app.common.constant import (
    DEFAULT_URLS_CONTENT,
    DEFAULT_CSV_OUTPUT,
    DEFAULT_OUTPUT_PKL,
    DEFAULT_OUTPUT_TREE,
    DEFAULT_OUTPUT_FLAT
)

def safe(val):
    """Make any value JSON-serialisable."""
    try:
        if isinstance(val, (str, int, float, bool)) or val is None:
            return val
        return str(val)
    except Exception as e:
        print(Msg.SAFE_ERROR.format(e))
        return str(val)

class CreateGraphBot:
    def __init__(self, urls_content, csv_output, output_pkl, output_tree, output_flat):
        self.URLS_CONTENT = urls_content
        self.CSV_OUTPUT = csv_output
        self.OUTPUT_PKL = output_pkl
        self.OUTPUT_TREE = output_tree
        self.OUTPUT_FLAT = output_flat
    
        os.makedirs(os.path.dirname(self.OUTPUT_PKL), exist_ok=True)
        os.makedirs(os.path.dirname(self.OUTPUT_TREE), exist_ok=True)

    def parse_url_parts(self, url):
        try:
            parsed = urlparse(url)
            path   = parsed.path.strip('/')
            parts  = [p for p in path.split('/') if p] if path else []
            domain = parsed.netloc or url
            return domain, parts
        except Exception:
            return url, []
    
    def to_csv(self):
        try:
            final_df = pd.DataFrame()

            for file in os.listdir(self.URLS_CONTENT):
                print(file)
                with open(os.path.join(self.URLS_CONTENT, file), "r") as f:
                    content_dict = {}
                    for data in f.readlines():
                        data = json.loads(data)

                        key = list(data.keys())[0]
                        content = list(data.values())[0]
                        content_dict[key] = content
                
                df = (
                    pd.DataFrame([content_dict])
                    .T
                    .reset_index()
                    .rename(columns={
                        "index" : "url",
                        0 : "content"
                    })
                    .assign(
                        section=lambda df_: df_['url'].apply(
                            lambda x: x.split("/")[3] if isinstance(x, str) and len(x.split("/")) > 3 else 'unknown'
                        ),
                        heading=lambda df_: df_['content'].apply(
                            lambda x: x.split("\n")[0] if isinstance(x, str) and x else ''
                        ),
                    )
                    .sort_values(by=['section'], ascending=True)
                )
                
                final_df = pd.concat([final_df, df], ignore_index=True)
                final_df.to_csv(self.CSV_OUTPUT, index=False)
        except Exception as e:
            print(Msg.TO_CSV_ERROR.format(e))

    def to_pickle(self):
        try:
            df = pd.read_csv(self.CSV_OUTPUT)
            G = nx.DiGraph()
            for _, row in df.iterrows():
                url = row['url']
                section = row['section']
                heading = str(row.get('heading', '')).strip()[:60] if 'heading' in row else ''
                content = str(row.get('content', '')).strip() if 'content' in row else ''
                content = '' if content == 'nan' else content

                domain, parts = self.parse_url_parts(url)

                # Root domain node
                if not G.has_node(domain):
                    G.add_node(domain, label=domain, node_type='domain', depth=0, content='')

                prev = domain
                for depth, part in enumerate(parts, start=1):
                    node_id   = domain + '/' + '/'.join(parts[:depth])
                    is_leaf   = (depth == len(parts))
                    
                    if not G.has_node(node_id):
                        base_url = f"https://{domain}"
                        current_path = '/'.join(parts[:depth])
                        constructed_url = f"{base_url}/{current_path}" if current_path else base_url
                        G.add_node(node_id,
                            label=part,
                            node_type='page' if is_leaf else 'section',
                            depth=depth,
                            section=section,
                            full_url=constructed_url,   # ✅ FIXED
                            content=content if is_leaf else ''
                        )
                    
                    else:
                        # If node already exists and this is the leaf, attach content
                        if is_leaf and not G.nodes[node_id].get('content'):
                            G.nodes[node_id]['content'] = content

                    if not G.has_edge(prev, node_id):
                        G.add_edge(prev, node_id, relation='contains')
                    prev = node_id

                # Heading nodes attached to leaf page (with content snippet)
                if heading and heading != 'nan' and parts:
                    leaf       = domain + '/' + '/'.join(parts)
                    heading_id = f"heading::{heading}"
                    if not G.has_node(heading_id):
                        G.add_node(heading_id,
                                label=heading,
                                node_type='heading',
                                depth=len(parts) + 1,
                                content=content)
                    if not G.has_edge(leaf, heading_id):
                        G.add_edge(leaf, heading_id, relation='has_heading')
                
            with open(self.OUTPUT_PKL, 'wb') as f:
                pickle.dump(G, f)
        except Exception as e:
            print(Msg.TO_PICKLE_ERROR.format(e))
        
    def to_json(self):
        try:
            def build_tree(graph: nx.DiGraph, root: str) -> dict:
                try:
                    attrs = graph.nodes[root]
                    return {
                        "id":        root,
                        "label":     safe(attrs.get("label", root)),
                        "node_type": safe(attrs.get("node_type", "unknown")),
                        "depth":     safe(attrs.get("depth", -1)),
                        "section":   safe(attrs.get("section")),
                        "full_url":  safe(attrs.get("full_url")),
                        "content":   safe(attrs.get("content", "")),
                        "children":  [build_tree(graph, child)
                        for _, child in sorted(graph.out_edges(root))],
                    }
                except Exception as e:
                    print(Msg.BUILD_TREE_ERROR.format(e))
                    return {}
            
            print(Msg.LOADING_PICKLE)
            with open(self.OUTPUT_PKL, "rb") as f:
                G: nx.DiGraph = pickle.load(f)

            depth_dist = defaultdict(int)
            for _, d in G.nodes(data=True):
                depth_dist[d.get("depth", -1)] += 1

            section_dist = defaultdict(int)
            for _, d in G.nodes(data=True):
                sec = d.get("section")
                if sec:
                    section_dist[sec] += 1

            summary = {
                "total_nodes":          G.number_of_nodes(),
                "total_edges":          G.number_of_edges(),
                "max_depth":            max(depth_dist.keys()),
                "depth_distribution":   {str(k): v for k, v in sorted(depth_dist.items())},
                "section_distribution": dict(
                    sorted(section_dist.items(), key=lambda x: -x[1])
                ),
            }
            
            roots = [n for n in G.nodes() if G.in_degree(n) == 0]
            print(f"Tree roots  : {roots}")

            tree_output = {
                "summary": summary,
                "tree":    [build_tree(G, r) for r in roots],
            }

            with open(self.OUTPUT_TREE, "w", encoding="utf-8") as f:
                json.dump(tree_output, f, indent=2, ensure_ascii=False)

            print(Msg.TREE_JSON_SAVED.format(self.OUTPUT_TREE))
        except Exception as e:
            print(Msg.TO_JSON_ERROR.format(e))
    
if __name__ == "__main__":
    bot = CreateGraphBot(
        urls_content=DEFAULT_URLS_CONTENT,
        csv_output=DEFAULT_CSV_OUTPUT,
        output_pkl=DEFAULT_OUTPUT_PKL,
        output_tree=DEFAULT_OUTPUT_TREE,
        output_flat=DEFAULT_OUTPUT_FLAT
    )
    bot.to_csv()
    bot.to_pickle()
    bot.to_json()
