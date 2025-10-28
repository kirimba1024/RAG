#!/bin/sh
set -e

echo "[sandbox] Starting RAG sandbox..."

# Функция для копирования данных из внешнего источника
copy_knowledge_data() {
  echo "[sandbox] Copying knowledge data..."
  
  # Проверяем, есть ли данные в /tmp/knowledge (если переданы через volume)
  if [ -d "/tmp/knowledge" ] && [ "$(ls -A /tmp/knowledge)" ]; then
    echo "[sandbox] Found knowledge data in /tmp/knowledge, copying..."
    cp -r /tmp/knowledge/* /app/ 2>/dev/null || true
    echo "[sandbox] Knowledge data copied successfully"
  else
    echo "[sandbox] No external knowledge data found, using empty directory"
    # Создаем базовую структуру
    mkdir -p /app
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
