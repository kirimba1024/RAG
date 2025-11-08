from typing import List
from pathlib import Path
import math

import torch
from elasticsearch import Elasticsearch
from llama_index.core.base.base_retriever import BaseRetriever
from llama_index.core.schema import QueryBundle, BaseNode, TextNode, NodeWithScore
from llama_index.core import Settings
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.postprocessor.sbert_rerank import SentenceTransformerRerank

from utils import ES_URL, ES_INDEX_CHUNKS, EMBED_MODEL, RERANK_MODEL, setup_logging

logger = setup_logging(Path(__file__).stem)

FIELD_WEIGHTS = {
    "symbols": 5.5,
    "paths": 4.5,
    "api_endpoints": 4.5,
    "keys": 3.5,
    "db_entities": 3.5,
    "dependencies": 3.5,
    "events_queues": 3.5,
    "idents": 1.5,
    "headers_auth_scopes": 1.5,
    "errors_codes": 1.5,
    "imports": 1.5,
    "functions": 1.5,
    "classes": 1.5,
    "variables": 1.5,
    "feature_flags": 1.5,
    "secrets": 1.5,
    "permissions": 1.5,
    "roles": 1.5,
    "config_keys": 1.5,
    "dtos": 1.5,
    "entities": 1.5,
    "domain_objects": 1.5,
    "io": 1.5,
    "tags": 0.75,
    "key_points": 0.75,
    "security_flags": 1.5,
    "todos": 0.75,
}

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
    def __init__(self, es, index, path_prefix: str, top_k: int, signals):
        super().__init__()
        self.es = es
        self.index = index
        self.top_k = top_k
        self.path_prefix = normal_prefix(path_prefix)
        self.signals = signals

    def _retrieve(self, query_bundle: QueryBundle) -> List[NodeWithScore]:
        query_embedding = Settings.embed_model.get_text_embedding(query_bundle.query_str)
        base_filter = [{"range": {"chunk_id": {"gte": 1}}}]
        filters = base_filter + ([{"prefix": {"path": self.path_prefix}}] if self.path_prefix else [])
        should_clauses = [{"multi_match": {"query": query_bundle.query_str, "fields": ["text^1.0", "text.ru^1.3", "text.en^1.2"]}}]
        query_terms = [t.lower() for t in query_bundle.query_str.split() if t.isalnum()]
        if query_terms:
            should_clauses.append({"terms": {"bm25_boost_terms": query_terms, "boost": 1.5}})
        if self.signals:
            for field_name, values in self.signals.items():
                if values and field_name in FIELD_WEIGHTS:
                    should_clauses.append({"terms": {field_name: values, "boost": FIELD_WEIGHTS[field_name]}})
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

def retrieve_fusion_nodes(question: str, path_prefix: str, top_n: int, signals) -> List[BaseNode]:
    retriever = HybridESRetriever(es=ES, index=ES_INDEX_CHUNKS, path_prefix=path_prefix, top_k=top_n * 3, signals=signals)
    candidates = retriever.retrieve(question)
    logger.info(f"🔍 Retriever вернул {len(candidates)} чанков (query: '{question[:50]}...')")
    qb = QueryBundle(query_str=question)
    RERANKER.top_n = top_n
    reranked = RERANKER.postprocess_nodes(candidates, query_bundle=qb)
    logger.info(f"⭐ Reranker отобрал {len(reranked)} чанков из {len(candidates)}")
    return [nws.node for nws in reranked]

def main_search(question: str, path_prefix: str, top_n: int, signals, fields, show_line_numbers) -> str:
    nodes = retrieve_fusion_nodes(question, path_prefix, top_n, signals)
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
        if fields:
            for field in fields:
                if field in meta and meta[field]:
                    result_text += f"\n\n[{field}]: {meta[field]}"
        results.append(result_text)
    return "\n\n".join(results)

def safe_number(v, d=0):
    if v is None:
        return 0
    if isinstance(v, float) and math.isnan(v):
        return 0
    return v

def code_stats(path_prefix: str = "") -> str:
    query = {
        "size": 0,
        "query": {"bool": {"filter": ([{"prefix": {"path": path_prefix}}] if path_prefix else [{"match_all": {}}])}},
        "runtime_mappings": {
            "chunk_len": {
                "type": "long",
                "script": """
                  long end = doc['end_line'].size()!=0 ? doc['end_line'].value : 0;
                  long beg = doc['start_line'].size()!=0 ? doc['start_line'].value : 0;
                  emit(end>=beg ? (end - beg + 1) : 0);
                """
            },
            "top_dir": {
                "type": "keyword",
                "script": """
                  if (doc['path'].size()==0) { emit('_unknown'); return; }
                  String p = doc['path'].value;
                  int s = p.indexOf('/');
                  emit(s>0 ? p.substring(0,s) : p);
                """
            }
        },
        "aggs": {
            "files": {"cardinality": {"field": "path", "precision_threshold": 40000}},
            "chunks": {"value_count": {"field": "chunk_id"}},
            "by_file": {
                "terms": {"field": "path", "size": 65535, "execution_hint": "map"},
                "aggs": {
                    "max_file_size": {"max": {"field": "file_size"}},
                    "max_file_lines": {"max": {"field": "file_lines"}}
                }
            },
            "total_file_size_exact": {"sum_bucket": {"buckets_path": "by_file>max_file_size"}},
            "total_file_lines_exact": {"sum_bucket": {"buckets_path": "by_file>max_file_lines"}},
            "total_chunk_size": {"sum": {"field": "size"}},
            "chunk_len_stats": {"extended_stats": {"field": "chunk_len"}},
            "chunk_len_pct": {"percentiles": {"field": "chunk_len", "percents": [50, 90, 99]}},
            "by_lang": {
                "terms": {"field": "lang", "size": 20, "missing": "unknown", "order": {"lines": "desc"}},
                "aggs": {
                    "files": {"cardinality": {"field": "path"}},
                    "chunks": {"value_count": {"field": "chunk_id"}},
                    "lines": {"sum": {"field": "chunk_len"}},
                    "complexity_avg": {"avg": {"field": "complexity"}},
                    "confidence_avg": {"avg": {"field": "confidence"}},
                    "len_p50": {"percentiles": {"field": "chunk_len", "percents": [50, 90]}},
                    "docs_cov": {
                        "filters": {
                            "filters": {
                                "with_docs": {"term": {"has_documentation": True}},
                                "no_docs": {"bool": {"must_not": {"term": {"has_documentation": True}}}}
                            }
                        }
                    }
                }
            },
            "by_ext": {
                "terms": {"field": "extension", "size": 20, "missing": "none", "order": {"lines": "desc"}},
                "aggs": {
                    "files": {"cardinality": {"field": "path"}},
                    "lines": {"sum": {"field": "chunk_len"}},
                    "len_p50": {"percentiles": {"field": "chunk_len", "percents": [50, 90]}}
                }
            },
            "by_dir": {
                "terms": {"field": "top_dir", "size": 15, "order": {"lines": "desc"}},
                "aggs": {
                    "files": {"cardinality": {"field": "path"}},
                    "chunks": {"value_count": {"field": "chunk_id"}},
                    "lines": {"sum": {"field": "chunk_len"}},
                    "updated_monthly": {
                        "date_histogram": {
                            "field": "updated_at",
                            "calendar_interval": "month",
                            "min_doc_count": 0
                        }
                    }
                }
            },
            "updated_monthly": {
                "date_histogram": {
                    "field": "updated_at",
                    "calendar_interval": "month",
                    "min_doc_count": 0
                },
                "aggs": {"lines": {"sum": {"field": "chunk_len"}}}
            },
            "dups": {
                "terms": {"field": "hash", "size": 10, "min_doc_count": 2, "exclude": "", "order": {"_count": "desc"}},
                "aggs": {
                    "examples": {"top_hits": {"size": 3, "_source": {"includes": ["path", "start_line", "end_line"]}}}
                }
            },
            "top_api": {"terms": {"field": "api_endpoints", "size": 15, "exclude": ""}},
            "top_db": {"terms": {"field": "db_entities", "size": 15, "exclude": ""}},
            "sampled_deps": {
                "sampler": {"shard_size": 5000},
                "aggs": {"top_deps": {"terms": {"field": "dependencies", "size": 15, "exclude": ""}}}
            },
            "signals_presence": {
                "filters": {
                    "filters": {
                        "secrets": {"exists": {"field": "secrets"}},
                        "security_flags": {"exists": {"field": "security_flags"}},
                        "permissions": {"exists": {"field": "permissions"}},
                        "roles": {"exists": {"field": "roles"}},
                        "feature_flags": {"exists": {"field": "feature_flags"}},
                        "todos": {"exists": {"field": "todos"}},
                        "bugs": {"exists": {"field": "bugs"}},
                        "vuln_text": {"exists": {"field": "vulnerabilities"}}
                    }
                }
            },
            "llm_versions": {
                "terms": {"field": "llm_version", "size": 10, "missing": "unknown"},
                "aggs": {
                    "chunks": {"value_count": {"field": "chunk_id"}},
                    "complexity_avg": {"avg": {"field": "complexity"}},
                    "confidence_avg": {"avg": {"field": "confidence"}}
                }
            },
            "kinds": {"terms": {"field": "kind", "size": 10, "missing": "unknown"}},
            "top_symbols": {"terms": {"field": "symbols", "size": 20, "exclude": ""}},
            "top_functions": {"terms": {"field": "functions", "size": 20, "exclude": ""}},
            "top_classes": {"terms": {"field": "classes", "size": 20, "exclude": ""}},
            "layers": {"terms": {"field": "layer", "size": 10, "missing": "unknown"}},
            "top_files": {
                "terms": {"field": "path", "size": 10, "order": {"chunk_count": "desc"}, "execution_hint": "map"},
                "aggs": {"chunk_count": {"value_count": {"field": "chunk_id"}}}
            },
            "largest_files": {
                "terms": {"field": "path", "size": 5, "order": {"max_lines": "desc"}, "execution_hint": "map"},
                "aggs": {"max_lines": {"max": {"field": "file_lines"}}, "file_size": {"max": {"field": "file_size"}}}
            }
        }
    }
    response = ES.search(index=ES_INDEX_CHUNKS, body=query, request_timeout=60, request_cache=True)
    aggs = response["aggregations"]
    results = [f"📊 Статистика кодовой базы" + (f" ({path_prefix})" if path_prefix else "")]
    results.extend([
        f"📁 Файлов: {aggs['files']['value']}",
        f"📄 Чанков: {aggs['chunks']['value']}",
        ""
    ])
    total_file_size_mb = safe_number(aggs['total_file_size_exact']['value']) / 1024 / 1024
    total_chunk_size_mb = safe_number(aggs['total_chunk_size']['value']) / 1024 / 1024
    len_stats = aggs['chunk_len_stats']
    len_pct = aggs['chunk_len_pct']['values']
    results.extend([
        f"💾 Размеры:",
        f"  Общий размер файлов (уникально по path): {total_file_size_mb:.2f} MB",
        f"  Общий размер чанков (сумма по чанкам): {total_chunk_size_mb:.2f} MB",
        f"  Всего строк (сумма по чанкам): {int(safe_number(len_stats['sum']))}",
        ""
    ])
    min_v = safe_number(len_stats['min'])
    max_v = safe_number(len_stats['max'])
    avg_v = safe_number(len_stats['avg'])
    std_v = safe_number(len_stats['std_deviation'])
    p50 = safe_number(len_pct.get('50.0'))
    p90 = safe_number(len_pct.get('90.0'))
    p99 = safe_number(len_pct.get('99.0'))
    results.extend([
        f"📏 Длина чанков (строки):",
        f"  min: {min_v:.0f}, max: {max_v:.0f}, avg: {avg_v:.1f}, stddev: {std_v:.1f}",
        f"  p50: {p50:.0f}, p90: {p90:.0f}, p99: {p99:.0f}",
        ""
    ])
    if aggs['by_lang']['buckets']:
        results.append("🌐 Языки программирования:")
        for bucket in aggs['by_lang']['buckets']:
            lang = bucket['key']
            files = bucket['files']['value']
            chunks = bucket['chunks']['value']
            lines = bucket['lines']['value']
            p50 = safe_number(bucket['len_p50']['values'].get('50.0'))
            docs_cov = bucket['docs_cov']
            with_docs = docs_cov['buckets']['with_docs']['doc_count']
            total_docs = with_docs + docs_cov['buckets']['no_docs']['doc_count']
            docs_pct = (with_docs * 100 / total_docs) if total_docs > 0 else 0
            complexity = bucket['complexity_avg']['value']
            confidence = bucket['confidence_avg']['value']
            complexity_str = f", сложность: {safe_number(complexity):.2f}" if complexity is not None else ""
            confidence_str = f", уверенность: {safe_number(confidence):.2f}" if confidence is not None else ""
            results.append(f"  {lang}: {files} файлов, {chunks} чанков, {lines:.0f} строк, p50: {p50:.0f}, docs: {docs_pct:.1f}%{complexity_str}{confidence_str}")
        results.append("")
    if aggs['by_ext']['buckets']:
        results.append("📝 Расширения файлов:")
        for bucket in aggs['by_ext']['buckets']:
            ext = bucket['key']
            ext_label = "<no-ext>" if ext == "none" else f".{ext}"
            files = bucket['files']['value']
            lines = bucket['lines']['value']
            p50 = safe_number(bucket['len_p50']['values'].get('50.0'))
            results.append(f"  {ext_label}: {files} файлов, {lines:.0f} строк, p50: {p50:.0f}")
        results.append("")
    if aggs['by_dir']['buckets']:
        results.append("📂 Топ директории:")
        for bucket in aggs['by_dir']['buckets']:
            dir_name = bucket['key']
            files = bucket['files']['value']
            chunks = bucket['chunks']['value']
            lines = bucket['lines']['value']
            months_buckets = bucket['updated_monthly']['buckets']
            months = len(months_buckets)
            last_month = months_buckets[-1]['key_as_string'] if months_buckets else ""
            last_month_str = f", последнее: {last_month}" if last_month else ""
            results.append(f"  {dir_name}: {files} файлов, {chunks} чанков, {lines:.0f} строк, обновлений: {months} мес.{last_month_str}")
        results.append("")
    if aggs['updated_monthly']['buckets']:
        results.append("📅 Активность по месяцам:")
        for bucket in aggs['updated_monthly']['buckets'][-6:]:
            date = bucket['key_as_string']
            lines = bucket['lines']['value']
            results.append(f"  {date}: {lines:.0f} строк")
        results.append("")
    if aggs['dups']['buckets']:
        results.append("🔄 Дубликаты (по hash):")
        for bucket in aggs['dups']['buckets']:
            hash_val = bucket['key'][:8]
            count = bucket['doc_count']
            examples = bucket['examples']['hits']['hits']
            results.append(f"  {hash_val}... ({count} чанков):")
            for ex in examples[:3]:
                path = ex['_source']['path']
                start = ex['_source']['start_line']
                end = ex['_source']['end_line']
                results.append(f"    {path} L:{start}-{end}")
        results.append("")
    if aggs['top_api']['buckets']:
        results.append("🌐 Топ API endpoints:")
        for bucket in aggs['top_api']['buckets'][:15]:
            results.append(f"  {bucket['key']}: {bucket['doc_count']} упоминаний")
        results.append("")
    if aggs['top_db']['buckets']:
        results.append("🗄️ Топ DB entities:")
        for bucket in aggs['top_db']['buckets'][:15]:
            results.append(f"  {bucket['key']}: {bucket['doc_count']} упоминаний")
        results.append("")
    if aggs['sampled_deps']['top_deps']['buckets']:
        results.append("📦 Топ dependencies:")
        for bucket in aggs['sampled_deps']['top_deps']['buckets'][:15]:
            results.append(f"  {bucket['key']}: {bucket['doc_count']} упоминаний")
        results.append("")
    signals = aggs['signals_presence']['buckets']
    if any(b['doc_count'] > 0 for b in signals.values()):
        results.append("⚠️ Сигналы присутствия:")
        signal_names = {
            "secrets": "🔐 Секреты",
            "security_flags": "🛡️ Флаги безопасности",
            "permissions": "🔑 Права доступа",
            "roles": "👤 Роли",
            "feature_flags": "🚩 Feature flags",
            "todos": "📝 TODO",
            "bugs": "🐛 Баги",
            "vuln_text": "🔒 Уязвимости"
        }
        for key, name in signal_names.items():
            if key in signals and signals[key]['doc_count'] > 0:
                results.append(f"  {name}: {signals[key]['doc_count']} чанков")
        results.append("")
    if aggs['llm_versions']['buckets']:
        results.append("🤖 Версии пайплайна:")
        for bucket in aggs['llm_versions']['buckets']:
            version = bucket['key']
            chunks = bucket['chunks']['value']
            complexity = bucket['complexity_avg']['value']
            confidence = bucket['confidence_avg']['value']
            complexity_str = f", сложность: {safe_number(complexity):.2f}" if complexity is not None else ""
            confidence_str = f", уверенность: {safe_number(confidence):.2f}" if confidence is not None else ""
            results.append(f"  {version}: {chunks} чанков{complexity_str}{confidence_str}")
        results.append("")
    if aggs['kinds']['buckets']:
        results.append("📦 Типы блоков:")
        for bucket in aggs['kinds']['buckets']:
            results.append(f"  {bucket['key']}: {bucket['doc_count']} чанков")
        results.append("")
    if aggs['top_symbols']['buckets']:
        results.append("🔤 Топ символов:")
        for bucket in aggs['top_symbols']['buckets'][:15]:
            results.append(f"  {bucket['key']}: {bucket['doc_count']} упоминаний")
        results.append("")
    if aggs['top_functions']['buckets']:
        results.append("⚙️ Топ функций:")
        for bucket in aggs['top_functions']['buckets'][:15]:
            results.append(f"  {bucket['key']}: {bucket['doc_count']} упоминаний")
        results.append("")
    if aggs['top_classes']['buckets']:
        results.append("🏛️ Топ классов:")
        for bucket in aggs['top_classes']['buckets'][:15]:
            results.append(f"  {bucket['key']}: {bucket['doc_count']} упоминаний")
        results.append("")
    if aggs['layers']['buckets']:
        results.append("🏗️ Архитектурные слои:")
        for bucket in aggs['layers']['buckets']:
            results.append(f"  {bucket['key']}: {bucket['doc_count']} чанков")
        results.append("")
    sections = [
        ("📈 Топ файлов по чанкам:", aggs["top_files"]["buckets"], lambda x: f"  {x['key']}: {x['chunk_count']['value']} чанков"),
        ("📊 Самые большие файлы:", aggs["largest_files"]["buckets"], lambda x: f"  {x['key']}: {x['max_lines']['value']} строк ({x['file_size']['value'] / 1024 / 1024:.2f} MB)")
    ]
    for title, items, formatter in sections:
        if items:
            results.extend(["", title])
            for item in items:
                results.append(formatter(item))
    return "\n".join(results)