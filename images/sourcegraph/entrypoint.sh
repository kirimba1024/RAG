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

  src login "$SRC_URL" -u "${SOURCEGRAPH_INITIAL_SITE_ADMIN_USERNAME:-admin}" -p "${SOURCEGRAPH_INITIAL_SITE_ADMIN_PASSWORD:-password}" >/dev/null 2>&1 || return 0

  src api -query '{ externalServices { nodes { displayName } } }' 2>/dev/null \
    | grep -q "Local monorepo" && return 0

  src api -query 'mutation AddLocal($input: AddExternalServiceInput!) { addExternalService(input: $input) { id } }' \
    -vars '{"input": {"kind": "OTHER", "displayName": "Local monorepo", "config": "{\"url\": \"file:///var/opt/sourcegraph/monorepo\", \"repos\": [\"monorepo\"]}"}}' \
    >/dev/null 2>&1 || true

  echo "[sourcegraph] Local monorepo added"
}

main() {
  if [ "${PROVISION_REPOS}" != "1" ]; then
    exec /sbin/tini -- /server server "$@"
  fi
  /sbin/tini -- /server server "$@" &
  wait_for_sourcegraph
  add_local_monorepo
  wait
}

main "$@"
