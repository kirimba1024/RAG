#!/bin/sh
set -e

cd /app/repos

if [ -d ".graphrag" ] && [ -f ".graphrag/config.yaml" ]; then
    if [ "$FORCE_REINDEX" != "true" ]; then
        echo "[graphrag] Existing index found, skipping indexing."
        echo "[graphrag] To force reindex, set FORCE_REINDEX=true"
        echo "[graphrag] Container ready for queries. Use: docker exec -it <container> graphrag run query -t 'your question' -k 5"
        exec sleep infinity
    else
        echo "[graphrag] Force reindex enabled, removing existing index..."
        rm -rf .graphrag
    fi
fi

echo "[graphrag] Starting GraphRAG indexing..."

if [ ! -f ".graphrag/config.yaml" ]; then
    echo "[graphrag] Initializing GraphRAG..."
    graphrag init || true
fi

echo "[graphrag] Running index..."
OUTPUT=$(graphrag run index 2>&1)
EXIT_CODE=$?

if [ -n "$OUTPUT" ]; then
    echo "$OUTPUT"
fi

if [ $EXIT_CODE -ne 0 ]; then
    echo "[graphrag] Error: indexing failed with exit code $EXIT_CODE"
    exit $EXIT_CODE
fi

if [ -d ".graphrag" ]; then
    echo "[graphrag] Indexing completed successfully"
    echo "[graphrag] Container ready for queries. Use: docker exec -it <container> graphrag run query -t 'your question' -k 5"
else
    echo "[graphrag] Error: .graphrag directory not found after indexing"
    exit 1
fi

exec sleep infinity

