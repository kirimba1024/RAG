#!/bin/sh
set -e

create_indices() {
  for i in $(seq 1 60); do
    curl -fsS http://localhost:9200 >/dev/null 2>&1 && break
    sleep 1
  done
  
  curl -fsS -X PUT "http://localhost:9200/${ES_INDEX_CHUNKS:-chunks}" \
    -H 'Content-Type: application/json' \
    -d @/init/index_chunks.json >/dev/null 2>&1 || true

  curl -fsS -X PUT "http://localhost:9200/${ES_INDEX_FILE_MANIFEST:-file_manifest}" \
    -H 'Content-Type: application/json' \
    -d @/init/index_file_manifest.json >/dev/null 2>&1 || true

  echo "[elasticsearch] indices applied (chunks, file_manifest)"
}

create_indices &
exec /usr/local/bin/docker-entrypoint.sh
