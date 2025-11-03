#!/bin/sh
set -e

cd /app/monorepo

if [ -d ".graphrag" ] && [ -f ".graphrag/config.yaml" ]; then
    echo "[graphrag] Existing complete index found, skipping indexing."
    echo "[graphrag] Container ready for queries. Use: docker exec -it <container> graphrag query -t 'your question' -k 5"
    exec sleep infinity
fi

echo "[graphrag] Starting GraphRAG indexing..."

if [ ! -f "settings.yaml" ]; then
    echo "[graphrag] Initializing GraphRAG..."
    graphrag init || true
fi

if [ -f "settings.yaml" ]; then
    envsubst < settings.yaml > settings.yaml.tmp && mv settings.yaml.tmp settings.yaml
fi

echo "[graphrag] Running index..."
graphrag index 2>&1 || {
    echo "[graphrag] Error: indexing failed. Container will stay running for manual inspection."
    echo "[graphrag] Check logs or exec into container to debug"
}

if [ -d ".graphrag" ] && [ -f ".graphrag/config.yaml" ]; then
    echo "[graphrag] Indexing completed successfully"
    echo "[graphrag] Container ready for queries. Use: docker exec -it <container> graphrag query -t 'your question' -k 5"
else
    echo "[graphrag] Error: .graphrag directory not found after indexing"
    echo "[graphrag] Container will stay running. Check settings.yaml and try: graphrag index"
fi

exec sleep infinity
