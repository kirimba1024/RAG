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
    echo "[sandbox] No external knowledge data found, using empty directory"
    echo "# RAG Sandbox" > /app/README.md
    echo "This is a sandbox environment for RAG operations." >> /app/README.md
  fi
  
  # Устанавливаем права доступа
  chmod -R 755 /app
  chown -R nobody:nobody /app
  
  echo "[sandbox] Knowledge data ready at /app"
  echo "[sandbox] Available commands: grep, find, awk, sed, bash, curl, wget, jq, tree, file, git, diffutils"
}

# Копируем данные при старте
copy_knowledge_data

# Переключаемся на непривилегированного пользователя
echo "[sandbox] Sandbox ready! Use: docker exec -it <container> sh"

# Держим контейнер живым
exec sleep infinity
