#!/bin/sh
set -e

cd /app/repos

if [ -d ".graphrag" ] && [ -f ".graphrag/config.yaml" ]; then
    echo "[graphrag] Existing complete index found, skipping indexing."
    echo "[graphrag] Container ready for queries. Use: docker exec -it <container> graphrag run query -t 'your question' -k 5"
    exec sleep infinity
fi

echo "[graphrag] Starting GraphRAG indexing..."

if [ ! -f "settings.yaml" ]; then
    echo "[graphrag] Initializing GraphRAG..."
    graphrag init || true
fi

echo "[graphrag] Running index (will continue if interrupted)..."
graphrag run index 2>&1 || {
    echo "[graphrag] Error: indexing failed. Container will stay running for manual inspection."
    echo "[graphrag] You can exec into container and run: graphrag run index"
}

if [ -d ".graphrag" ] && [ -f ".graphrag/config.yaml" ]; then
    echo "[graphrag] Indexing completed successfully"
    echo "[graphrag] Container ready for queries. Use: docker exec -it <container> graphrag run query -t 'your question' -k 5"
else
    echo "[graphrag] Error: .graphrag directory not found after indexing"
    exit 1
fi

exec sleep infinity

