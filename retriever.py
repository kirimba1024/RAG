from typing import List
from pathlib import Path

import torch
from elasticsearch import Elasticsearch
from llama_index.core.schema import QueryBundle, BaseNode, TextNode, NodeWithScore
from llama_index.core import Settings
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.postprocessor.sbert_rerank import SentenceTransformerRerank

from utils import ES_URL, ES_INDEX_CHUNKS, EMBED_MODEL, RERANK_MODEL, setup_logging, to_posix

logger = setup_logging(Path(__file__).stem)

ES = Elasticsearch(ES_URL, request_timeout=30, max_retries=3, retry_on_timeout=True)

Settings.embed_model = HuggingFaceEmbedding(EMBED_MODEL, normalize=True)
embedding_dim = len(Settings.embed_model.get_text_embedding("test"))
if embedding_dim != 1024:
    raise ValueError(f"Несоответствие размерности эмбеддинга: модель {EMBED_MODEL} возвращает {embedding_dim}, а ES настроен на 1024. Измените dims в images/elasticsearch/index_chunks.json или используйте модель с размерностью 1024.")

DEVICE = "cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu"
RERANKER = SentenceTransformerRerank(model=RERANK_MODEL, top_n=10, device=DEVICE)

SOURCE_FIELDS = ["text", "path", "start_line", "end_line", "title", "symbols", "lang", "mime", "file_lines", "kind", "links_in", "links_out", "chunk_id", "chunks"]

def rrf_fusion(ranked_lists, k=60):
    pos = [{d: i for i, d in enumerate(lst)} for lst in ranked_lists]
    all_ids = set().union(*ranked_lists)
    scores = {d: sum(1.0 / (k + p[d] + 1) for p in pos if d in p) for d in all_ids}
    return sorted(scores, key=scores.get, reverse=True)

def retrieve_fusion_nodes(question: str, path_prefix: str, top_n: int, symbols, use_reranker) -> List[BaseNode]:
    shortlist = max(6 * top_n, 32) if use_reranker else top_n
    size = shortlist
    cleaned = path_prefix.replace("*", "") if path_prefix else ""
    normalized = to_posix(cleaned) if cleaned else ""
    path_filter = [{"prefix": {"path": normalized}}] if normalized else []
    should_clauses = [{"multi_match": {"query": question, "fields": ["text^1.0", "text.ru^1.3", "text.en^1.2"]}}]
    if symbols:
        should_clauses.append({"terms": {"symbols": [s.lower() for s in symbols if s]}})
    bm25_response = ES.search(
        index=ES_INDEX_CHUNKS,
        body={"size": size, "query": {"bool": {"filter": path_filter, "should": should_clauses, "minimum_should_match": 1}}, "_source": {"includes": SOURCE_FIELDS}}
    )
    bm25_hits = {hit["_id"]: hit for hit in bm25_response["hits"]["hits"]}
    query_embedding = Settings.embed_model.get_text_embedding(question)
    knn_config = {"field": "embedding", "query_vector": query_embedding, "k": size, "num_candidates": shortlist * 4}
    if path_filter:
        knn_config["filter"] = {"bool": {"must": path_filter}}
    knn_response = ES.search(index=ES_INDEX_CHUNKS, body={"size": size, "knn": knn_config, "_source": {"includes": SOURCE_FIELDS}})
    knn_hits = {hit["_id"]: hit for hit in knn_response["hits"]["hits"]}
    fused_ids = rrf_fusion([bm25_hits.keys(), knn_hits.keys()])[:shortlist]
    all_hits = {**bm25_hits, **knn_hits}
    candidates = [NodeWithScore(node=TextNode(id_=doc_id, text=all_hits[doc_id]["_source"]["text"], metadata=dict(all_hits[doc_id]["_source"])), score=0.0) for doc_id in fused_ids]
    logger.info(f"🔗 RRF: bm25={len(bm25_hits)} knn={len(knn_hits)} → shortlist={len(candidates)}")
    if use_reranker and candidates:
        RERANKER.top_n = top_n
        result = [nws.node for nws in RERANKER.postprocess_nodes(candidates, query_bundle=QueryBundle(query_str=question))]
        logger.info(f"✨ top_n={top_n} → returned={len(result)} (⭐ reranked)")
        return result
    result = [nws.node for nws in candidates[:top_n]]
    logger.info(f"✨ top_n={top_n} → returned={len(result)}")
    return result

def format_chunk_data(doc_id, metadata):
    return {
        "id": doc_id,
        **{k: v for k, v in metadata.items() if k in set(SOURCE_FIELDS)}
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
