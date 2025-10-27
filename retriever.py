from typing import List
from pathlib import Path

import torch
from elasticsearch import Elasticsearch
from llama_index.core.base.base_retriever import BaseRetriever
from llama_index.core.schema import QueryBundle, BaseNode, TextNode, NodeWithScore
from llama_index.core import Settings
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.postprocessor.sbert_rerank import SentenceTransformerRerank

from utils import ES_URL, ES_INDEX, EMBED_MODEL, RERANK_MODEL, setup_logging

logger = setup_logging(Path(__file__).stem)

ES = Elasticsearch(ES_URL, request_timeout=30, max_retries=3, retry_on_timeout=True)

Settings.embed_model = HuggingFaceEmbedding(EMBED_MODEL, normalize=True)

DEVICE = "cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu"
RERANKER = SentenceTransformerRerank(model=RERANK_MODEL, top_n=10, device=DEVICE)

def normal_prefix(id_prefix):
    return (id_prefix or "").lstrip("/").lstrip(".")


class HybridESRetriever(BaseRetriever):
    def __init__(self, es, index, top_k=20, path_prefix: str = ""):
        super().__init__()
        self.es = es
        self.index = index
        self.top_k = top_k
        self.path_prefix = normal_prefix(path_prefix)

    def _retrieve(self, query_bundle: QueryBundle) -> List[NodeWithScore]:
        query_embedding = Settings.embed_model.get_text_embedding(query_bundle.query_str)
        body = {
            "size": self.top_k,
            "knn": {
                "field": "embedding",
                "query_vector": query_embedding,
                "k": self.top_k,
                "num_candidates": self.top_k * 5,
            },
            "query": {
                "bool": {
                    "should": [
                        {
                            "multi_match": {
                                "query": query_bundle.query_str,
                                "fields": ["text^1.0", "text.ru^1.3", "text.en^1.2"],
                            }
                        }
                    ]
                }
            }
        }
        if self.path_prefix:
            body["query"]["bool"]["filter"] = [{"prefix": {"doc_id": self.path_prefix}}]
            body["knn"]["filter"] = {"prefix": {"doc_id": self.path_prefix}}
        response = self.es.search(
            index=self.index,
            knn=body["knn"],
            query=body["query"],
            size=body["size"],
            request_timeout=30
        )
        nodes = []
        for hit in response["hits"]["hits"]:
            source = hit["_source"]
            metadata = source.get("metadata", {}).copy()
            metadata["doc_id"] = source.get("doc_id")
            node = TextNode(id_=hit["_id"], text=source["text"], metadata=metadata)
            nodes.append(NodeWithScore(node=node, score=float(hit["_score"])))
        return nodes


def retrieve_fusion_nodes(question: str, path_prefix: str = "") -> List[BaseNode]:
    retriever = HybridESRetriever(es=ES, index=ES_INDEX, top_k=30, path_prefix=path_prefix)
    candidates = retriever.retrieve(question)
    logger.info(f"🔍 Retriever вернул {len(candidates)} чанков (query: '{question[:50]}...')")
    qb = QueryBundle(query_str=question)
    reranked = RERANKER.postprocess_nodes(candidates, query_bundle=qb)
    logger.info(f"⭐ Reranker отобрал {len(reranked)} чанков из {len(candidates)}")
    return [nws.node for nws in reranked]


def nodes_to_text(nodes: List[BaseNode]) -> str:
    results = []
    for node in nodes:
        doc_id = node.metadata['doc_id']
        chunk_info = f"[chunk {node.metadata['chunk_id']}/{node.metadata['chunk_total']}]"
        line_info = f"Lines {node.metadata['start_line']}-{node.metadata['end_line']}"
        header = f"{doc_id} {chunk_info} {line_info}"
        results.append(f"{header}:\n{node.text}")
    return "\n\n".join(results)
