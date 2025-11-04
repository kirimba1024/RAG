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
embedding_dim = len(Settings.embed_model.get_text_embedding("test"))
if embedding_dim != 1024:
    raise ValueError(f"Несоответствие размерности эмбеддинга: модель {EMBED_MODEL} возвращает {embedding_dim}, а ES настроен на 1024. Измените dims в images/elasticsearch/index.json или используйте модель с размерностью 1024.")

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
        filters = []
        if self.path_prefix:
            filters.append({"prefix": {"path": self.path_prefix}})
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
        if filters:
            body["query"]["bool"]["filter"] = filters
            knn_filter = {"bool": {"must": filters}}
            body["knn"]["filter"] = knn_filter
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
            metadata = {
                "doc_id": source.get("path"),
                "chunk_id": source.get("chunk_id"),
                "chunk_count": source.get("chunks"),
                "start_line": source.get("start_line"),
                "end_line": source.get("end_line"),
            }
            node = TextNode(id_=hit["_id"], text=source["text"], metadata=metadata)
            nodes.append(NodeWithScore(node=node, score=float(hit["_score"])))
        return nodes

def retrieve_fusion_nodes(question: str, path_prefix: str, top_n: int) -> List[BaseNode]:
    retriever = HybridESRetriever(es=ES, index=ES_INDEX, path_prefix=path_prefix, top_k=top_n * 3)
    candidates = retriever.retrieve(question)
    logger.info(f"🔍 Retriever вернул {len(candidates)} чанков (query: '{question[:50]}...')")
    qb = QueryBundle(query_str=question)
    RERANKER.top_n = top_n
    reranked = RERANKER.postprocess_nodes(candidates, query_bundle=qb)
    logger.info(f"⭐ Reranker отобрал {len(reranked)} чанков из {len(candidates)}")
    return [nws.node for nws in reranked]


def get_code_stats(path_prefix: str = "") -> str:
    """Базовая статистика кодовой базы"""
    query_filter = {"prefix": {"path": path_prefix}} if path_prefix else {"match_all": {}}
    query = {
        "size": 0,
        "query": query_filter,
        "aggs": {
            "files": {"cardinality": {"field": "path"}},
            "chunks": {"value_count": {"field": "_id"}},
            "top_files": {
                "terms": {"field": "path", "size": 10},
                "aggs": {"chunk_count": {"value_count": {"field": "chunk_id"}}}
            },
            "avg_chunk_size": {"avg": {"field": "end_line"}},
            "largest_files": {
                "terms": {"field": "path", "size": 5},
                "aggs": {"max_lines": {"max": {"field": "end_line"}}}
            }
        }
    }
    response = ES.search(index=ES_INDEX, body=query)
    aggs = response["aggregations"]
    results = [f"📊 Базовая статистика" + (f" ({path_prefix})" if path_prefix else "")]
    results.extend([
        f"📁 Файлов: {aggs['files']['value']}",
        f"📄 Чанков: {aggs['chunks']['value']}",
        f"📏 Средний размер чанка: {aggs['avg_chunk_size']['value'] or 0:.0f} строк",
        ""
    ])
    sections = [
        ("📈 Топ файлов по чанкам:", aggs["top_files"]["buckets"], lambda x: f"  {x['key']}: {x['chunk_count']['value']} чанков"),
        ("📊 Самые большие файлы:", aggs["largest_files"]["buckets"], lambda x: f"  {x['key']}: {x['max_lines']['value']} строк")
    ]
    for title, items, formatter in sections:
        results.extend(["", title])
        for item in items:
            results.append(formatter(item))
    return "\n".join(results)