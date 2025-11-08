from typing import List, Dict, Set, Tuple
from collections import defaultdict
from pathlib import Path
from elasticsearch.helpers import bulk
import numpy as np

from utils import ES_URL, ES_INDEX_CHUNKS, setup_logging, EMBED_MODEL
from elasticsearch import Elasticsearch
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

logger = setup_logging(Path(__file__).stem)

ES = Elasticsearch(ES_URL, request_timeout=30, max_retries=3, retry_on_timeout=True)
EMBEDDING = HuggingFaceEmbedding(EMBED_MODEL, normalize=True)

MAX_LINKS_PER_CHUNK = 5
QA_SIMILARITY_THRESHOLD = 0.7

def qa_similarity(answers: List[str], questions: List[str], qa_embeddings: Dict[str, np.ndarray]) -> Tuple[float, str, str]:
    if not answers or not questions:
        return (0.0, "", "")
    similarities = []
    for ans in answers:
        if ans not in qa_embeddings:
            continue
        for q in questions:
            if q not in qa_embeddings:
                continue
            sim = np.dot(qa_embeddings[ans], qa_embeddings[q])
            similarities.append((sim, ans, q))
    return max(similarities, default=(0.0, "", ""))

def main():
    logger.info("Загрузка всех сигналов чанков в память")
    chunk_symbols = {}
    chunk_qa = {}
    qa_embeddings = {}
    query = {"size": 10000, "_source": ["symbols", "graph_questions", "graph_answers"], "query": {"match_all": {}}}
    scroll = ES.search(index=ES_INDEX_CHUNKS, body=query, scroll="5m", size=1000)
    scroll_id = scroll.get("_scroll_id")
    hits = scroll["hits"]["hits"]
    while len(hits) > 0:
        for hit in hits:
            source = hit["_source"]
            chunk_id = hit["_id"]
            chunk_symbols[chunk_id] = set(source.get("symbols", []))
            questions = source.get("graph_questions", [])
            answers = source.get("graph_answers", [])
            chunk_qa[chunk_id] = {"questions": questions, "answers": answers}
            for text in questions + answers:
                if text not in qa_embeddings:
                    qa_embeddings[text] = EMBEDDING.get_text_embedding(text)
        scroll = ES.scroll(scroll_id=scroll_id, scroll="5m")
        hits = scroll["hits"]["hits"]
    ES.clear_scroll(scroll_id=scroll_id)
    logger.info(f"Загружено {len(chunk_symbols)} чанков, построение графа")
    chunk_ids = list(chunk_symbols.keys())
    graph = defaultdict(list)
    graph_qa = defaultdict(list)
    for i, chunk_id1 in enumerate(chunk_ids):
        symbols1 = chunk_symbols[chunk_id1]
        qa1 = chunk_qa[chunk_id1]
        for chunk_id2 in chunk_ids[i+1:]:
            symbols2 = chunk_symbols[chunk_id2]
            qa2 = chunk_qa[chunk_id2]
            intersection = symbols1 & symbols2
            if intersection:
                graph[chunk_id1].append({"target": chunk_id2, "symbols": list(intersection)})
                graph[chunk_id2].append({"target": chunk_id1, "symbols": list(intersection)})
            sim1, ans1, q1 = qa_similarity(qa1["answers"], qa2["questions"], qa_embeddings)
            sim2, ans2, q2 = qa_similarity(qa2["answers"], qa1["questions"], qa_embeddings)
            sim, ans, q = max((sim1, ans1, q1), (sim2, ans2, q2))
            if sim >= QA_SIMILARITY_THRESHOLD:
                graph_qa[chunk_id1].append({"target": chunk_id2, "similarity": sim, "answer": ans, "question": q})
                graph_qa[chunk_id2].append({"target": chunk_id1, "similarity": sim, "answer": ans, "question": q})
        if (i + 1) % 100 == 0:
            logger.debug(f"Обработано {i + 1}/{len(chunk_ids)} чанков")
    filtered = {}
    filtered_qa = {}
    for chunk_id, links in graph.items():
        filtered[chunk_id] = sorted(links, key=lambda x: len(x["symbols"]), reverse=True)[:MAX_LINKS_PER_CHUNK]
    for chunk_id, links in graph_qa.items():
        filtered_qa[chunk_id] = sorted(links, key=lambda x: x["similarity"], reverse=True)[:MAX_LINKS_PER_CHUNK]
    total_edges = sum(len(links) for links in filtered.values()) // 2
    total_qa_edges = sum(len(links) for links in filtered_qa.values()) // 2
    logger.info(f"Граф построен: {len(filtered)} узлов, {total_edges} рёбер, {total_qa_edges} QA рёбер")
    actions = []
    for chunk_id in chunk_ids:
        actions.append({
            "_op_type": "update",
            "_index": ES_INDEX_CHUNKS,
            "_id": chunk_id,
            "doc": {
                "links": filtered.get(chunk_id, []),
                "links_qa": filtered_qa.get(chunk_id, [])
            }
        })
    if actions:
        bulk(ES, actions, chunk_size=1000, request_timeout=120)
        logger.info(f"Обновлено {len(actions)} чанков с полями links и links_qa")

if __name__ == "__main__":
    main()

