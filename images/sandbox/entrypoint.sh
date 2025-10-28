#!/bin/sh
set -e

echo "[sandbox] Starting RAG sandbox..."

# Функция для копирования данных из внешнего источника
copy_knowledge_data() {
  echo "[sandbox] Copying knowledge data..."
  
  # Проверяем, есть ли данные в /app (если переданы через volume)
  if [ -d "/app" ] && [ "$(ls -A /app)" ]; then
    echo "[sandbox] Found knowledge data in /app, ready to use"
    echo "[sandbox] Knowledge data ready at /app"
  else
    echo "[sandbox] No external knowledge data found"
    echo "[sandbox] Please mount knowledge data to /app"
  fi
  
  echo "[sandbox] Available commands: grep, find, awk, sed, bash, curl, wget, jq, tree, file, diffutils"
}

# Копируем данные при старте
copy_knowledge_data

# Переключаемся на непривилегированного пользователя
echo "[sandbox] Sandbox ready! Use: docker exec -it <container> sh"

# Держим контейнер живым
exec sleep infinity
