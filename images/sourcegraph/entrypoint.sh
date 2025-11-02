#!/bin/sh
set -e

SRC_URL="http://127.0.0.1:7080"

wait_for_sourcegraph() {
  echo "[sourcegraph] Waiting for Sourcegraph..."
  for i in $(seq 1 120); do
    curl -fsS "$SRC_URL/healthz" >/dev/null 2>&1 && break
    sleep 2
  done
  curl -fsS "$SRC_URL/healthz" >/dev/null 2>&1 || echo "[sourcegraph] Warning: health check failed, continuing anyway"
}

add_local_monorepo() {
  [ -d /var/opt/sourcegraph/monorepo/.git ] || return 0

  curl -fsS "$SRC_URL/.api/graphql" \
    -u "${SOURCEGRAPH_INITIAL_SITE_ADMIN_USERNAME:-admin}:${SOURCEGRAPH_INITIAL_SITE_ADMIN_PASSWORD:-password}" \
    -H "Content-Type: application/json" \
    -d '{"query":"{ externalServices { nodes { displayName } } }"}' \
    | grep -q "Local monorepo" && return 0

  cat > /tmp/add-local-repo.json <<'JSON'
{
  "query": "mutation AddLocal($input: AddExternalServiceInput!) { addExternalService(input: $input) { id } }",
  "variables": {
    "input": {
      "kind": "OTHER",
      "displayName": "Local monorepo",
      "config": "{\n  \"url\": \"file:///var/opt/sourcegraph/monorepo\",\n  \"repos\": [\"monorepo\"]\n}"
    }
  }
}
JSON

  curl -fsS -X POST "$SRC_URL/.api/graphql" \
    -u "${SOURCEGRAPH_INITIAL_SITE_ADMIN_USERNAME:-admin}:${SOURCEGRAPH_INITIAL_SITE_ADMIN_PASSWORD:-password}" \
    -H "Content-Type: application/json" \
    --data-binary @/tmp/add-local-repo.json >/dev/null 2>&1 || true

  echo "[sourcegraph] Local monorepo added"
}

main() {
  if [ "${PROVISION_REPOS}" != "1" ]; then
    exec /sbin/tini -- /server server "$@"
  fi
  wait_for_sourcegraph
  add_local_monorepo
  exec /sbin/tini -- /server server "$@"
}

main "$@"
