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
  SRC_URL="http://localhost:3080"
  ADMIN_USER="${SOURCEGRAPH_INITIAL_SITE_ADMIN_USERNAME:-admin}"
  ADMIN_PASS="${SOURCEGRAPH_INITIAL_SITE_ADMIN_PASSWORD:-password}"

  # Ждем готовности
  wait_for_sourcegraph

  # Логинимся src cli (создаст сессию)
  if ! src login "$SRC_URL" -u "$ADMIN_USER" -p "$ADMIN_PASS" >/dev/null 2>&1; then
    echo "[sourcegraph] src login failed (maybe site not initialized yet)."
  fi

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

  # Добавляем локальные репозитории как file://
  if [ -d "/var/opt/sourcegraph/repos" ]; then
    find /var/opt/sourcegraph/repos -maxdepth 2 -type d -name .git | while read -r gitdir; do
      repo_dir="$(dirname "$gitdir")"
      name="local/$(basename "$repo_dir")"
      url="file://$repo_dir"
      echo "[sourcegraph] Adding repo $name -> $url"
      src repos add -name "$name" -url "$url" >/dev/null 2>&1 || true
    done
  fi

  date > "$FLAG_FILE"
  echo "[sourcegraph] Provisioning done"
}

# Запускаем провижининг в фоне
provision_if_needed &

# Запускаем оригинальный entrypoint Sourcegraph
# Если используется sourcegraph/server, путь может отличаться
exec /usr/bin/sourcegraph-server || exec /usr/local/bin/sourcegraph-server || exec /entrypoint.sh
