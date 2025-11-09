from typing import List
from pathlib import Path

import torch
from elasticsearch import Elasticsearch
from llama_index.core.base.base_retriever import BaseRetriever
from llama_index.core.schema import QueryBundle, BaseNode, TextNode, NodeWithScore
from llama_index.core import Settings
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.postprocessor.sbert_rerank import SentenceTransformerRerank

from utils import ES_URL, ES_INDEX_CHUNKS, EMBED_MODEL, RERANK_MODEL, setup_logging

logger = setup_logging(Path(__file__).stem)

ES = Elasticsearch(ES_URL, request_timeout=30, max_retries=3, retry_on_timeout=True)

Settings.embed_model = HuggingFaceEmbedding(EMBED_MODEL, normalize=True)
embedding_dim = len(Settings.embed_model.get_text_embedding("test"))
if embedding_dim != 1024:
    raise ValueError(f"Несоответствие размерности эмбеддинга: модель {EMBED_MODEL} возвращает {embedding_dim}, а ES настроен на 1024. Измените dims в images/elasticsearch/index_chunks.json или используйте модель с размерностью 1024.")

DEVICE = "cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu"
RERANKER = SentenceTransformerRerank(model=RERANK_MODEL, top_n=10, device=DEVICE)

def normal_prefix(id_prefix):
    return (id_prefix or "").lstrip("/").lstrip(".")

class HybridESRetriever(BaseRetriever):
    def __init__(self, es, index, path_prefix: str, top_k: int):
        super().__init__()
        self.es = es
        self.index = index
        self.top_k = top_k
        self.path_prefix = normal_prefix(path_prefix)

    def _retrieve(self, query_bundle: QueryBundle, symbols) -> List[NodeWithScore]:
        query_embedding = Settings.embed_model.get_text_embedding(query_bundle.query_str)
        base_filter = [{"range": {"chunk_id": {"gte": 1}}}]
        filters = base_filter + ([{"prefix": {"path": self.path_prefix}}] if self.path_prefix else [])
        should_clauses = [{"multi_match": {"query": query_bundle.query_str, "fields": ["text^1.0", "text.ru^1.3", "text.en^1.2"]}}]
        query_terms = [t.lower() for t in query_bundle.query_str.split() if t.isalnum()]
        if query_terms:
            should_clauses.append({"terms": {"bm25_boost_terms": query_terms, "boost": 1.5}})
            should_clauses.append({"terms": {"symbols": query_terms, "boost": 2.0}})
        if symbols:
            symbol_terms = [s.lower() for s in symbols if s]
            should_clauses.append({"terms": {"symbols": symbol_terms, "boost": 2.5}})
        knn_config = {"field": "embedding", "query_vector": query_embedding, "k": self.top_k, "num_candidates": self.top_k * 5}
        if filters:
            knn_config["filter"] = {"bool": {"must": filters}}
        response = self.es.search(
            index=self.index,
            knn=knn_config,
            query={"bool": {"filter": filters, "should": should_clauses}},
            size=self.top_k,
            request_timeout=30
        )
        return [NodeWithScore(node=TextNode(id_=hit["_id"], text=hit["_source"]["text"], metadata=dict(hit["_source"])), score=float(hit["_score"])) for hit in response["hits"]["hits"]]

def retrieve_fusion_nodes(question: str, path_prefix: str, top_n: int, symbols, use_reranker) -> List[BaseNode]:
    top_k = top_n * 3 if use_reranker else top_n
    retriever = HybridESRetriever(es=ES, index=ES_INDEX_CHUNKS, path_prefix=path_prefix, top_k=top_k)
    qb = QueryBundle(query_str=question)
    candidates = retriever._retrieve(qb, symbols)
    logger.info(f"🔍 Retriever вернул {len(candidates)} чанков (query: '{question[:50]}...')")
    if use_reranker:
        RERANKER.top_n = top_n
        reranked = RERANKER.postprocess_nodes(candidates, query_bundle=qb)
        logger.info(f"⭐ Reranker отобрал {len(reranked)} чанков из {len(candidates)}")
        return [nws.node for nws in reranked]
    return [nws.node for nws in candidates[:top_n]]

def format_chunk_data(chunk_id, metadata):
    whitelist = {"text", "path", "start_line", "end_line", "file_lines", "kind", "lang", "mime", "title", "links"}
    return {
        "chunk_id": chunk_id,
        **{k: v for k, v in metadata.items() if k in whitelist}
    }

def get_chunks(chunk_ids):
    if not chunk_ids:
        return []
    response = ES.mget(
        index=ES_INDEX_CHUNKS,
        body={"ids": chunk_ids},
        request_timeout=30
    )
    return [format_chunk_data(doc["_id"], doc["_source"]) for doc in response["docs"] if doc["found"]]

def main_search(question: str, path_prefix: str, top_n: int, symbols, use_reranker):
    nodes = retrieve_fusion_nodes(question, path_prefix, top_n, symbols, use_reranker)
    return [format_chunk_data(node.id_, node.metadata) for node in nodes]
