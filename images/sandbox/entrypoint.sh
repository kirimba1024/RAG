#!/bin/sh
set -e

echo "[sandbox] Starting RAG sandbox..."

# Функция для проверки данных из внешнего источника
check_repos_data() {
  echo "[sandbox] Checking repos data..."
  
  # Проверяем, есть ли данные в /app (если переданы через volume)
  if [ -d "/app" ] && [ "$(ls -A /app)" ]; then
    echo "[sandbox] Found repos data in /app, ready to use"
    echo "[sandbox] Repos ready at /app"
  else
    echo "[sandbox] No external repos data found"
    echo "[sandbox] Please mount repos to /app"
  fi
  
  echo "[sandbox] Available commands: grep, find, awk, sed, bash, curl, wget, jq, tree, file, diffutils"
}

# Проверяем данные при старте
check_repos_data

# Переключаемся на непривилегированного пользователя
echo "[sandbox] Sandbox ready! Use: docker exec -it <container> sh"

# Держим контейнер живым
exec sleep infinity
