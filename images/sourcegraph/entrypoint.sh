#!/bin/sh
set -e

REPO_DIR=/var/opt/sourcegraph/monorepo

if [ -d "$REPO_DIR/.git" ]; then
  src serve-git -addr=127.0.0.1:3434 "$REPO_DIR" >/var/log/src-serve-git.log 2>&1 &
  for i in 1 2 3 4 5; do
    curl -fsS http://127.0.0.1:3434/ >/dev/null 2>&1 && break
    sleep 0.2
  done
fi

exec /sbin/tini -- /server server "$@"
