from typing import List, Dict, Set, Tuple
from collections import defaultdict
from pathlib import Path

from utils import ES_URL, ES_INDEX_CHUNKS, setup_logging
from elasticsearch import Elasticsearch

logger = setup_logging(Path(__file__).stem)

ES = Elasticsearch(ES_URL, request_timeout=30, max_retries=3, retry_on_timeout=True)

FIELD_WEIGHTS = {
    "symbols": 11.0,
    "paths": 9.0,
    "api_endpoints": 9.0,
    "keys": 8.0,
    "db_entities": 8.0,
    "dependencies": 7.0,
    "events_queues": 7.0,
    "idents": 5.0,
    "headers_auth_scopes": 5.0,
    "errors_codes": 5.0,
    "imports": 4.0,
    "functions": 4.0,
    "classes": 4.0,
    "variables": 4.0,
    "feature_flags": 4.0,
    "secrets": 4.0,
    "permissions": 4.0,
    "roles": 4.0,
    "apis": 3.0,
    "endpoints": 3.0,
    "config_keys": 3.0,
    "dtos": 3.0,
    "entities": 3.0,
    "domain_objects": 3.0,
    "bm25_boost_terms": 3.0,
    "io": 2.0,
    "tags": 1.0,
    "key_points": 1.0,
    "likely_queries": 1.0,
    "security_flags": 1.0,
    "todos": 1.0,
}

def get_chunk_signals(chunk_id: str) -> Dict[str, Set[str]]:
    response = ES.get(index=ES_INDEX_CHUNKS, id=chunk_id)
    source = response["_source"]
    signals = {}
    for field in FIELD_WEIGHTS.keys():
        values = source.get(field, [])
        if isinstance(values, list):
            signals[field] = set(values)
        else:
            signals[field] = set()
    return signals

def compute_edge_weight(chunk1_signals: Dict[str, Set[str]], chunk2_signals: Dict[str, Set[str]]) -> Tuple[float, Dict[str, Dict], Dict[str, float]]:
    total_weight = 0.0
    matched_fields = {}
    field_contributions = {}
    for field in FIELD_WEIGHTS.keys():
        set1 = chunk1_signals.get(field, set())
        set2 = chunk2_signals.get(field, set())
        intersection = set1 & set2
        if intersection:
            field_weight = FIELD_WEIGHTS.get(field, 1.0)
            match_count = len(intersection)
            weight = field_weight * match_count
            total_weight += weight
            field_contributions[field] = weight
            matched_fields[field] = {
                "count": match_count,
                "values": list(intersection),
                "contribution": weight
            }
    return total_weight, matched_fields, field_contributions

def build_chunk_graph(chunk_ids: List[str], min_weight: float = 5.0) -> Dict[str, List[Dict]]:
    logger.info(f"Построение графа для {len(chunk_ids)} чанков")
    chunk_signals = {}
    for chunk_id in chunk_ids:
        try:
            chunk_signals[chunk_id] = get_chunk_signals(chunk_id)
        except Exception as e:
            logger.warning(f"Не удалось загрузить сигналы для {chunk_id}: {e}")
            chunk_signals[chunk_id] = {field: set() for field in FIELD_WEIGHTS.keys()}
    graph = defaultdict(list)
    processed = 0
    for i, chunk_id1 in enumerate(chunk_ids):
        if chunk_id1 not in chunk_signals:
            continue
        signals1 = chunk_signals[chunk_id1]
        for chunk_id2 in chunk_ids[i+1:]:
            if chunk_id2 not in chunk_signals:
                continue
            signals2 = chunk_signals[chunk_id2]
            weight, matched_fields, field_contributions = compute_edge_weight(signals1, signals2)
            if weight >= min_weight:
                sorted_fields = sorted(field_contributions.items(), key=lambda x: x[1], reverse=True)
                graph[chunk_id1].append({
                    "target": chunk_id2,
                    "weight": weight,
                    "fields": matched_fields,
                    "field_contributions": field_contributions,
                    "top_fields": [field for field, _ in sorted_fields]
                })
                graph[chunk_id2].append({
                    "target": chunk_id1,
                    "weight": weight,
                    "fields": matched_fields,
                    "field_contributions": field_contributions,
                    "top_fields": [field for field, _ in sorted_fields]
                })
        processed += 1
        if processed % 100 == 0:
            logger.debug(f"Обработано {processed}/{len(chunk_ids)} чанков")
    total_edges = sum(len(edges) for edges in graph.values()) // 2
    logger.info(f"Граф построен: {len(graph)} узлов, {total_edges} рёбер (min_weight={min_weight})")
    return dict(graph)

def filter_top_connections(graph: Dict[str, List[Dict]], max_edges_per_node: int = 5) -> Dict[str, List[Dict]]:
    filtered = {}
    for chunk_id, edges in graph.items():
        sorted_edges = sorted(edges, key=lambda x: x["weight"], reverse=True)
        filtered[chunk_id] = sorted_edges[:max_edges_per_node]
    total_edges = sum(len(edges) for edges in filtered.values()) // 2
    logger.info(f"Отфильтровано до {len(filtered)} узлов, {total_edges} рёбер (max_edges_per_node={max_edges_per_node})")
    return filtered

def process_chunk_graph(chunk_ids: List[str], min_weight: float = 5.0, max_edges_per_node: int = 5) -> Dict[str, List[Dict]]:
    graph = build_chunk_graph(chunk_ids, min_weight)
    filtered_graph = filter_top_connections(graph, max_edges_per_node)
    return filtered_graph

