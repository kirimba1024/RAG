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
    chunk_questions = {}
    chunk_answers = {}
    qa_embeddings = {}
    query = {"size": 100000, "_source": ["graph_questions", "graph_answers"], "query": {"match_all": {}}}
    scroll = ES.search(index=ES_INDEX_CHUNKS, body=query, scroll="5m", size=1000)
    scroll_id = scroll.get("_scroll_id")
    hits = scroll["hits"]["hits"]
    while len(hits) > 0:
        for hit in hits:
            source = hit["_source"]
            chunk_id = hit["_id"]
            questions = source["graph_questions"]
            answers = source["graph_answers"]
            chunk_questions[chunk_id] = questions
            chunk_answers[chunk_id] = answers
            for text in questions + answers:
                if text not in qa_embeddings:
                    qa_embeddings[text] = EMBEDDING.get_text_embedding(text)
        scroll = ES.scroll(scroll_id=scroll_id, scroll="5m")
        hits = scroll["hits"]["hits"]
    ES.clear_scroll(scroll_id=scroll_id)
    logger.info(f"Загружено {len(chunk_questions)} чанков, построение графа")
    chunk_ids = list(chunk_questions.keys())
    edges_out = defaultdict(list)
    edges_in = defaultdict(list)
    for i, chunk_id1 in enumerate(chunk_ids):
        for j, chunk_id2 in enumerate(chunk_ids):
            if i == j: continue
            for question in chunk_questions[chunk_id1]:
                for answer in chunk_answers[chunk_id2]:
                    similarity = np.dot(qa_embeddings[answer], qa_embeddings[question])
                    if similarity >= QA_SIMILARITY_THRESHOLD:
                        edges_out[chunk_id1].append({"target": chunk_id2, "similarity": similarity, "answer": answer, "question": question})
                        edges_in[chunk_id2].append({"target": chunk_id1, "similarity": similarity, "answer": answer, "question": question})
        if (i + 1) % 100 == 0:
            logger.debug(f"Обработано {i + 1}/{len(chunk_ids)} чанков")
    links_out = {chunk_id: sorted(edges_out[chunk_id], key=lambda x: x["similarity"], reverse=True)[:MAX_LINKS_PER_CHUNK] for chunk_id in chunk_ids}
    links_in = {chunk_id: sorted(edges_in[chunk_id], key=lambda x: x["similarity"], reverse=True)[:MAX_LINKS_PER_CHUNK] for chunk_id in chunk_ids}
    total_edges = sum(len(links) for links in links_out.values())
    logger.info(f"Граф построен: {len(chunk_ids)} узлов, {total_edges} рёбер")
    actions = [
        {
            "_op_type": "update",
            "_index": ES_INDEX_CHUNKS,
            "_id": chunk_id,
            "doc": {
                "links_out": links_out[chunk_id],
                "links_in": links_in[chunk_id]
            }
        }
        for chunk_id in chunk_ids
    ]
    if actions:
        bulk(ES, actions, chunk_size=1000, request_timeout=120)
        logger.info(f"Обновлено {len(actions)} чанков с полями links_in/links_out")

if __name__ == "__main__":
    main()

