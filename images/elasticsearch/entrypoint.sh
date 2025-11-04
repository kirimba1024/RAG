#!/bin/sh
set -e

create_indices() {
  for i in $(seq 1 60); do
    curl -fsS http://localhost:9200 >/dev/null 2>&1 && break
    sleep 1
  done
  
  curl -fsS -X PUT "http://localhost:9200/${ES_INDEX:-rag}" \
    -H 'Content-Type: application/json' \
    -d @/init/index.json >/dev/null 2>&1 || true
  
  echo "[elasticsearch] rag index applied"
}

create_indices &
exec /usr/local/bin/docker-entrypoint.sh
