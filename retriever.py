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
    def __init__(self, es, index, path_prefix: str, top_k=20):
        super().__init__()
        self.es = es
        self.index = index
        self.top_k = top_k
        self.path_prefix = normal_prefix(path_prefix)

    def _retrieve(self, query_bundle: QueryBundle) -> List[NodeWithScore]:
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
            "languages": {"terms": {"field": "language.keyword", "size": 10}},
            "top_files": {
                "terms": {"field": "doc_id.keyword", "size": 10},
                "aggs": {"chunk_count": {"value_count": {"field": "metadata.chunk_id"}}}
            },
            "avg_chunk_size": {"avg": {"field": "metadata.end_line"}},
            "largest_files": {
                "terms": {"field": "doc_id.keyword", "size": 5},
                "aggs": {"max_lines": {"max": {"field": "metadata.end_line"}}}
            },
            "recent_files": {
                "terms": {"field": "doc_id.keyword", "size": 5},
            },
            "file_extensions": {
                "terms": {"field": "file_extension.keyword", "size": 10}
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
        "",
        "🌐 Языки:"
    ])
    # Добавляем все секции в цикле
    sections = [
        ("🌐 Языки:", aggs["languages"]["buckets"], lambda x: f"  {x['key']}: {x['doc_count']}"),
        ("📈 Топ файлов по чанкам:", aggs["top_files"]["buckets"], lambda x: f"  {x['key']}: {x['chunk_count']['value']} чанков"),
        ("📊 Самые большие файлы:", aggs["largest_files"]["buckets"], lambda x: f"  {x['key']}: {x['max_lines']['value']} строк"),
        ("📁 По расширениям:", aggs["file_extensions"]["buckets"], lambda x: f"  .{x['key']}: {x['doc_count']} файлов")
    ]
    
    for title, items, formatter in sections:
        results.extend(["", title])
        for item in items:
            results.append(formatter(item))
    
    return "\n".join(results)


def get_architecture_stats(path_prefix: str = "") -> str:
    """Архитектурная статистика кодовой базы"""
    query_filter = {"prefix": {"doc_id": path_prefix}} if path_prefix else {"match_all": {}}
    query = {
        "size": 0,
        "query": query_filter,
        "aggs": {
            "complexity_stats": {"stats": {"field": "complexity_score"}},
            "test_coverage": {"terms": {"field": "is_test_file", "size": 2}},
            "documentation_ratio": {"terms": {"field": "has_documentation", "size": 2}},
            "architecture_layers": {"terms": {"field": "layer.keyword", "size": 10}},
            "dependency_density": {"avg": {"field": "dependency_count"}},
            "code_duplication": {"terms": {"field": "is_duplicate", "size": 2}}
        }
    }
    response = ES.search(index=ES_INDEX, body=query)
    aggs = response["aggregations"]
    
    results = [f"🏗️ Архитектурная статистика" + (f" ({path_prefix})" if path_prefix else "")]
    
    results.extend(["", "🧮 Сложность кода:"])
    complexity = aggs["complexity_stats"]
    results.append(f"  Средняя: {complexity['avg'] or 0:.1f}")
    results.append(f"  Максимальная: {complexity['max'] or 0:.1f}")
    
    # Добавляем все секции в цикле
    sections = [
        ("🧪 Покрытие тестами:", aggs["test_coverage"]["buckets"], lambda x: f"  {'Тесты' if x['key'] else 'Основной код'}: {x['doc_count']} файлов"),
        ("📚 Документация:", aggs["documentation_ratio"]["buckets"], lambda x: f"  {'С документацией' if x['key'] else 'Без документации'}: {x['doc_count']} файлов"),
        ("🏗️ Архитектурные слои:", aggs["architecture_layers"]["buckets"], lambda x: f"  {x['key']}: {x['doc_count']} файлов"),
        ("🔄 Дублирование кода:", aggs["code_duplication"]["buckets"], lambda x: f"  {'Дублированный' if x['key'] else 'Уникальный'}: {x['doc_count']} файлов")
    ]
    
    for title, items, formatter in sections:
        results.extend(["", title])
        for item in items:
            results.append(formatter(item))
    
    results.extend(["", "🔗 Плотность зависимостей:"])
    results.append(f"  Средняя: {aggs['dependency_density']['value'] or 0:.1f} зависимостей на файл")
    
    return "\n".join(results)
