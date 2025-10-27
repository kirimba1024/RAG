#!/bin/sh
set -e

BOLT_HOST="bolt://localhost:7687"
AUTH="${NEO4J_AUTH:-neo4j/neo4jpass}"
if [ "$AUTH" = "none" ]; then
  AUTH_FLAGS=""
else
  USER="${AUTH%/*}"
  PASS="${AUTH#*/}"
  AUTH_FLAGS="-u $USER -p $PASS"
fi

# Стартуем сервер в фоне
/startup/docker-entrypoint.sh neo4j console &   # ← важно: запускаем официальный entrypoint
NEO4J_PID=$!

# Ждём Bolt и, если нужно, прогоняем init
echo "Waiting for Neo4j $BOLT_HOST ..."
until cypher-shell -a "$BOLT_HOST" -u "$USER" -p "$PASS" "RETURN 1" >/dev/null 2>&1; do
  sleep 1
done

if [ -f /docker-init/init.cypher ] && [ ! -f /data/.init_done ]; then
  echo "Running init Cypher..."
  cypher-shell -a "$BOLT_HOST" -u "$USER" -p "$PASS" < /docker-init/init.cypher || true
  touch /data/.init_done
fi

echo "[neo4j] init.cypher applied"

# Держим процесс
wait "$NEO4J_PID"