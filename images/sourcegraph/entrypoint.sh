#!/bin/sh
set -e

wait_for_sourcegraph() {
  echo "[sourcegraph] Waiting for Sourcegraph to be ready..."
  for i in $(seq 1 120); do
    curl -fsS http://localhost:3080/healthz >/dev/null 2>&1 && break
    sleep 2
  done
  
  if curl -fsS http://localhost:3080/healthz >/dev/null 2>&1; then
    echo "[sourcegraph] Sourcegraph is ready"
    echo "[sourcegraph] GraphQL API available at http://localhost:3080/.api/graphql"
  else
    echo "[sourcegraph] Warning: Sourcegraph health check failed"
  fi
}

# Ждем готовности Sourcegraph в фоне
wait_for_sourcegraph &

# Запускаем оригинальный entrypoint Sourcegraph
# Если используется sourcegraph/server, путь может отличаться
exec /usr/bin/sourcegraph-server || exec /usr/local/bin/sourcegraph-server || exec /entrypoint.sh
