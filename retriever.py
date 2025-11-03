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
    def __init__(self, es, index, path_prefix: str, top_k=20, neighbor_max_files=10, neighbor_min_cosine=0.35, per_file_multiplier=3):
        super().__init__()
        self.es = es
        self.index = index
        self.top_k = top_k
        self.path_prefix = normal_prefix(path_prefix)
        self.neighbor_max_files = neighbor_max_files
        self.neighbor_min_cosine = neighbor_min_cosine
        self.per_file_multiplier = per_file_multiplier

    def _retrieve(self, query_bundle: QueryBundle) -> List[NodeWithScore]:
        nodes = self._retrieve_bm25_knn(query_bundle)
        neighbor_nodes = self._get_neighbor_nodes(nodes)
        nodes = self._merge_nodes(nodes, neighbor_nodes)
        return nodes

    def _retrieve_bm25_knn(self, query_bundle: QueryBundle) -> List[NodeWithScore]:
        query_embedding = Settings.embed_model.get_text_embedding(query_bundle.query_str)
        filters = []
        if self.path_prefix:
            filters.append({"prefix": {"doc_id": self.path_prefix}})
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
            metadata = source.get("metadata", {}).copy()
            metadata["doc_id"] = source.get("doc_id")
            node = TextNode(id_=hit["_id"], text=source["text"], metadata=metadata)
            nodes.append(NodeWithScore(node=node, score=float(hit["_score"])))
        return nodes

    def _get_neighbor_nodes(
            self,
            nodes: List[NodeWithScore]
    ) -> List[TextNode]:
        seed_doc_ids = list({node.node.metadata.get("doc_id") for node in nodes if node.node.metadata.get("doc_id")})
        if not seed_doc_ids or self.neighbor_max_files <= 0:
            return []

        best_score_by_doc_id: dict[str, float] = {}

        for seed_doc_id in seed_doc_ids:
            seed_response = self.es.search(
                index=self.index,
                query={"term": {"doc_id": seed_doc_id}},
                size=1,
                request_timeout=15
            )
            seed_hits = seed_response["hits"]["hits"]
            if not seed_hits:
                continue

            seed_embedding = seed_hits[0]["_source"].get("embedding")
            if not seed_embedding:
                continue

            knn_query = {
                "field": "embedding",
                "query_vector": seed_embedding,
                "k": self.neighbor_max_files * 5,
                "num_candidates": self.neighbor_max_files * 10
            }

            neighbors_response = self.es.search(
                index=self.index,
                knn=knn_query,
                query={"match_all": {}},
                size=self.neighbor_max_files * 5,
                request_timeout=30
            )

            for neighbor_hit in neighbors_response["hits"]["hits"]:
                neighbor_doc_id = neighbor_hit["_source"].get("doc_id")
                neighbor_score = float(neighbor_hit.get("_score", 0.0))

                if not neighbor_doc_id:
                    continue
                if neighbor_doc_id == seed_doc_id:
                    continue
                if neighbor_score < self.neighbor_min_cosine:
                    continue

                current_best = best_score_by_doc_id.get(neighbor_doc_id, 0.0)
                if neighbor_score > current_best:
                    best_score_by_doc_id[neighbor_doc_id] = neighbor_score

        if not best_score_by_doc_id:
            return []

        sorted_pairs = sorted(
            best_score_by_doc_id.items(),
            key=lambda pair: pair[1],
            reverse=True
        )
        top_pairs = sorted_pairs[:self.neighbor_max_files]
        neighbor_doc_ids = [doc_id for doc_id, _ in top_pairs]

        should_terms = [{"term": {"doc_id": doc_id}} for doc_id in neighbor_doc_ids]

        chunks_response = self.es.search(
            index=self.index,
            query={"bool": {"should": should_terms, "minimum_should_match": 1}},
            size=len(neighbor_doc_ids) * self.per_file_multiplier,
            request_timeout=30
        )

        neighbor_nodes: List[TextNode] = []
        for hit in chunks_response["hits"]["hits"]:
            source = hit["_source"]
            metadata = (source.get("metadata") or {}).copy()
            metadata["doc_id"] = source.get("doc_id")
            neighbor_nodes.append(TextNode(id_=hit["_id"], text=source["text"], metadata=metadata))

        return neighbor_nodes

    @staticmethod
    def _merge_nodes(primary: list[NodeWithScore], neighbors: list[TextNode]) -> list[NodeWithScore]:
        return primary + [NodeWithScore(node=n, score=0.0) for n in neighbors]


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
    query_filter = {"prefix": {"doc_id": path_prefix}} if path_prefix else {"match_all": {}}
    query = {
        "size": 0,
        "query": query_filter,
        "aggs": {
            "files": {"cardinality": {"field": "doc_id.keyword"}},
            "chunks": {"value_count": {"field": "_id"}},
            "top_files": {
                "terms": {"field": "doc_id.keyword", "size": 10},
                "aggs": {"chunk_count": {"value_count": {"field": "metadata.chunk_id"}}}
            },
            "avg_chunk_size": {"avg": {"field": "metadata.end_line"}},
            "largest_files": {
                "terms": {"field": "doc_id.keyword", "size": 5},
                "aggs": {"max_lines": {"max": {"field": "metadata.end_line"}}}
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
