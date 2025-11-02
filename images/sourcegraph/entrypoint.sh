#!/bin/sh
set -e

wait_for_sourcegraph() {
  echo "[sourcegraph] Waiting for Sourcegraph to be ready..."
  for i in $(seq 1 120); do
    curl -fsS http://127.0.0.1:7080/healthz >/dev/null 2>&1 && break
    sleep 2
  done
  
  if curl -fsS http://127.0.0.1:7080/healthz >/dev/null 2>&1; then
    echo "[sourcegraph] Sourcegraph is ready"
    echo "[sourcegraph] GraphQL API available at http://127.0.0.1:7080/.api/graphql"
  else
    echo "[sourcegraph] Warning: Sourcegraph health check failed"
  fi
}

provision_if_needed() {
  if [ "${PROVISION_REPOS}" != "1" ]; then
    return 0
  fi

  FLAG_FILE="/var/opt/sourcegraph/.provisioned"
  if [ -f "$FLAG_FILE" ]; then
    echo "[sourcegraph] Provision already done, skipping"
    return 0
  fi

  echo "[sourcegraph] Starting provisioning..."
  SRC_URL="http://127.0.0.1:7080"
  ADMIN_USER="${SOURCEGRAPH_INITIAL_SITE_ADMIN_USERNAME:-admin}"
  ADMIN_PASS="${SOURCEGRAPH_INITIAL_SITE_ADMIN_PASSWORD:-password}"

  wait_for_sourcegraph
  
  for i in $(seq 1 10); do
    curl -fsS -X POST "$SRC_URL/.api/graphql" -H "Content-Type: application/json" -d '{"query":"query { site { id } }"}' >/dev/null 2>&1 && \
    src login "$SRC_URL" -u "$ADMIN_USER" -p "$ADMIN_PASS" >/dev/null 2>&1 && break
    [ $i -lt 10 ] && sleep 2
  done

  # Включаем автоиндексацию через site config
  set +e
  cat > /tmp/site-update.json <<'JSON'
{
  "codeIntelAutoIndexing": {
    "enabled": true
  }
}
JSON
  src config patch -autogit-ignore -f /tmp/site-update.json >/dev/null 2>&1
  set -e

  if [ -d "/var/opt/sourcegraph/monorepo/.git" ]; then
    echo "[sourcegraph] Adding monorepo"
    src repos add -name "monorepo" -url "file:///var/opt/sourcegraph/monorepo" >/dev/null 2>&1 || true
  fi

  date > "$FLAG_FILE"
  echo "[sourcegraph] Provisioning done"
}

# Запускаем провижининг в фоне
provision_if_needed &

# Запускаем оригинальный entrypoint Sourcegraph
exec /sbin/tini -- /server server "$@"
