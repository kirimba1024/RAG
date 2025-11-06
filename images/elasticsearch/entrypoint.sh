#!/bin/sh
set -e

create_indices() {
  for i in $(seq 1 60); do
    curl -fsS http://localhost:9200 >/dev/null 2>&1 && break
    sleep 1
  done
  
  # chunks index
  curl -fsS -X PUT "http://localhost:9200/${ES_INDEX_CHUNKS:-chunks}" \
    -H 'Content-Type: application/json' \
    -d @/init/index_chunks.json >/dev/null 2>&1 || true

  # files index
  curl -fsS -X PUT "http://localhost:9200/${ES_INDEX_FILES:-files}" \
    -H 'Content-Type: application/json' \
    -d @/init/index_files.json >/dev/null 2>&1 || true

  echo "[elasticsearch] indices applied (chunks, files)"
}

create_indices &
exec /usr/local/bin/docker-entrypoint.sh
