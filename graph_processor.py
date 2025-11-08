from typing import List, Dict, Set, Tuple
from collections import defaultdict
from pathlib import Path
from elasticsearch.helpers import bulk

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
    "config_keys": 3.0,
    "dtos": 3.0,
    "entities": 3.0,
    "domain_objects": 3.0,
    "bm25_boost_terms": 3.0,
    "io": 2.0,
    "tags": 1.0,
    "key_points": 1.0,
    "security_flags": 1.0,
    "todos": 1.0,
}

MIN_WEIGHT = 5.0
MAX_LINKS_PER_CHUNK = 5

def main():
    logger.info("Загрузка всех сигналов чанков в память")
    chunk_signals = {}
    query = {"size": 10000, "_source": list(FIELD_WEIGHTS.keys()), "query": {"match_all": {}}}
    scroll = ES.search(index=ES_INDEX_CHUNKS, body=query, scroll="5m", size=1000)
    scroll_id = scroll.get("_scroll_id")
    while len(scroll["hits"]["hits"]) > 0:
        for hit in scroll["hits"]["hits"]:
            source = hit["_source"]
            chunk_signals[hit["_id"]] = {field: set(source.get(field, [])) for field in FIELD_WEIGHTS.keys()}
        scroll = ES.scroll(scroll_id=scroll_id, scroll="5m")
    if scroll_id:
        ES.clear_scroll(scroll_id=scroll_id)
    logger.info(f"Загружено {len(chunk_signals)} чанков, построение графа")
    chunk_ids = list(chunk_signals.keys())
    graph = defaultdict(list)
    for i, chunk_id1 in enumerate(chunk_ids):
        signals1 = chunk_signals[chunk_id1]
        for chunk_id2 in chunk_ids[i+1:]:
            signals2 = chunk_signals[chunk_id2]
            total_weight = 0.0
            field_contributions = {}
            for field in FIELD_WEIGHTS.keys():
                intersection = signals1.get(field, set()) & signals2.get(field, set())
                if intersection:
                    weight = FIELD_WEIGHTS[field] * len(intersection)
                    total_weight += weight
                    field_contributions[field] = weight
            if total_weight >= MIN_WEIGHT:
                sorted_contributions = dict(sorted(field_contributions.items(), key=lambda x: x[1], reverse=True))
                graph[chunk_id1].append({"target": chunk_id2, "weight": total_weight, "field_contributions": sorted_contributions})
                graph[chunk_id2].append({"target": chunk_id1, "weight": total_weight, "field_contributions": sorted_contributions})
        if (i + 1) % 100 == 0:
            logger.debug(f"Обработано {i + 1}/{len(chunk_ids)} чанков")
    filtered = {chunk_id: sorted(edges, key=lambda x: x["weight"], reverse=True)[:MAX_LINKS_PER_CHUNK] for chunk_id, edges in graph.items()}
    total_edges = sum(len(edges) for edges in filtered.values()) // 2
    logger.info(f"Граф построен: {len(filtered)} узлов, {total_edges} рёбер")
    actions = [{"_op_type": "update", "_index": ES_INDEX_CHUNKS, "_id": chunk_id, "doc": {"links": links}} for chunk_id, links in filtered.items()]
    if actions:
        bulk(ES, actions, chunk_size=1000, request_timeout=120)
        logger.info(f"Обновлено {len(actions)} чанков с полем links")

if __name__ == "__main__":
    main()

