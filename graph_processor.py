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

def main():
    logger.info("Загрузка всех чанков в память")
    chunk_qa = {}
    qa_embeddings = {}
    query = {"size": 10000, "_source": ["graph_questions", "graph_answers"], "query": {"match_all": {}}}
    scroll = ES.search(index=ES_INDEX_CHUNKS, body=query, scroll="5m", size=1000)
    scroll_id = scroll.get("_scroll_id")
    hits = scroll["hits"]["hits"]
    while len(hits) > 0:
        for hit in hits:
            source = hit["_source"]
            chunk_id = hit["_id"]
            questions = source.get("graph_questions", [])
            answers = source.get("graph_answers", [])
            chunk_qa[chunk_id] = {"questions": questions, "answers": answers}
            for text in questions + answers:
                if text not in qa_embeddings:
                    qa_embeddings[text] = EMBEDDING.get_text_embedding(text)
        scroll = ES.scroll(scroll_id=scroll_id, scroll="5m")
        hits = scroll["hits"]["hits"]
    ES.clear_scroll(scroll_id=scroll_id)
    logger.info(f"Загружено {len(chunk_qa)} чанков, построение графа")
    chunk_ids = list(chunk_qa.keys())
    graph = defaultdict(list)
    for i, chunk_id1 in enumerate(chunk_ids):
        qa1 = chunk_qa[chunk_id1]
        for chunk_id2 in chunk_ids[i+1:]:
            qa2 = chunk_qa[chunk_id2]
            similarities = []
            for ans in qa1["answers"]:
                if ans not in qa_embeddings:
                    continue
                for q in qa2["questions"]:
                    if q in qa_embeddings:
                        similarities.append((np.dot(qa_embeddings[ans], qa_embeddings[q]), ans, q))
            for ans in qa2["answers"]:
                if ans not in qa_embeddings:
                    continue
                for q in qa1["questions"]:
                    if q in qa_embeddings:
                        similarities.append((np.dot(qa_embeddings[ans], qa_embeddings[q]), ans, q))
            if similarities:
                sim, ans, q = max(similarities)
                if sim >= QA_SIMILARITY_THRESHOLD:
                    link_data = {"target": chunk_id2, "similarity": sim, "answer": ans, "question": q}
                    graph[chunk_id1].append(link_data)
                    graph[chunk_id2].append({"target": chunk_id1, "similarity": sim, "answer": ans, "question": q})
        if (i + 1) % 100 == 0:
            logger.debug(f"Обработано {i + 1}/{len(chunk_ids)} чанков")
    filtered = {chunk_id: sorted(links, key=lambda x: x["similarity"], reverse=True)[:MAX_LINKS_PER_CHUNK] for chunk_id, links in graph.items()}
    total_edges = sum(len(links) for links in filtered.values()) // 2
    logger.info(f"Граф построен: {len(filtered)} узлов, {total_edges} рёбер")
    actions = [{"_op_type": "update", "_index": ES_INDEX_CHUNKS, "_id": chunk_id, "doc": {"links": filtered.get(chunk_id, [])}} for chunk_id in chunk_ids]
    if actions:
        bulk(ES, actions, chunk_size=1000, request_timeout=120)
        logger.info(f"Обновлено {len(actions)} чанков с полем links")

if __name__ == "__main__":
    main()

