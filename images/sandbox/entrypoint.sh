#!/bin/sh
set -e

echo "[sandbox] Starting RAG sandbox..."
echo "[sandbox] Monorepo ready at /app/monorepo"
echo "[sandbox] Available commands: grep, find, awk, sed, bash, curl, wget, jq, tree, file, diffutils"
echo "[sandbox] Sandbox ready! Use: docker exec -it <container> sh"

# Держим контейнер живым
exec sleep infinity
