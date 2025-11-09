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

    def _retrieve(self, query_bundle: QueryBundle) -> List[NodeWithScore]:
        query_embedding = Settings.embed_model.get_text_embedding(query_bundle.query_str)
        base_filter = [{"range": {"chunk_id": {"gte": 1}}}]
        filters = base_filter + ([{"prefix": {"path": self.path_prefix}}] if self.path_prefix else [])
        should_clauses = [{"multi_match": {"query": query_bundle.query_str, "fields": ["text^1.0", "text.ru^1.3", "text.en^1.2"]}}]
        query_terms = [t.lower() for t in query_bundle.query_str.split() if t.isalnum()]
        if query_terms:
            should_clauses.append({"terms": {"bm25_boost_terms": query_terms, "boost": 1.5}})
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

def retrieve_fusion_nodes(question: str, path_prefix: str, top_n: int) -> List[BaseNode]:
    retriever = HybridESRetriever(es=ES, index=ES_INDEX_CHUNKS, path_prefix=path_prefix, top_k=top_n * 3)
    candidates = retriever.retrieve(question)
    logger.info(f"🔍 Retriever вернул {len(candidates)} чанков (query: '{question[:50]}...')")
    qb = QueryBundle(query_str=question)
    RERANKER.top_n = top_n
    reranked = RERANKER.postprocess_nodes(candidates, query_bundle=qb)
    logger.info(f"⭐ Reranker отобрал {len(reranked)} чанков из {len(candidates)}")
    return [nws.node for nws in reranked]

def main_search(question: str, path_prefix: str, top_n: int, show_line_numbers, show_links) -> str:
    nodes = retrieve_fusion_nodes(question, path_prefix, top_n)
    results = []
    for node in nodes:
        meta = node.metadata
        header_parts = [
            node.id_,
            f"L:{meta['start_line']}-{meta['end_line']}/{meta['file_lines']}",
            f"kind:{meta['kind']}",
            f"lang:{meta['lang']}",
            f"mime:{meta['mime']}",
            f"size:{meta['size'] / 1048576:.2f}/{meta['file_size'] / 1048576:.2f}mb"
        ]
        text = node.text
        if show_line_numbers:
            start_line = meta['start_line']
            text = '\n'.join(f"{start_line + i:4d} | {line}" for i, line in enumerate(text.split('\n')))
        result_text = f"{' '.join(header_parts)}:\n{text}"
        if show_links and "links" in meta and meta["links"]:
            result_text += f"\n\n[links]: {meta['links']}"
        results.append(result_text)
    return "\n\n".join(results)
