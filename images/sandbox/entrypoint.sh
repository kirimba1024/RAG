#!/bin/sh
set -e

echo "[sandbox] Starting RAG sandbox..."

# Функция для копирования данных из внешнего источника
copy_knowledge_data() {
  echo "[sandbox] Copying knowledge data..."
  
  # Проверяем, есть ли данные в /tmp/knowledge (если переданы через volume)
  if [ -d "/tmp/knowledge" ] && [ "$(ls -A /tmp/knowledge)" ]; then
    echo "[sandbox] Found knowledge data in /tmp/knowledge, copying..."
    cp -r /tmp/knowledge/* / 2>/dev/null || true
    echo "[sandbox] Knowledge data copied successfully"
  else
    echo "[sandbox] No external knowledge data found, using empty directory"
    echo "# RAG Sandbox" > /README.md
    echo "This is a sandbox environment for RAG operations." >> /README.md
  fi
  
  # Устанавливаем права доступа
  chmod -R 755 /
  chown -R nobody:nobody /
  
  echo "[sandbox] Knowledge data ready at root"
  echo "[sandbox] Available commands: grep, find, awk, sed, bash, curl, wget, jq, tree, file, git, diffutils"
}

# Копируем данные при старте
copy_knowledge_data

# Переключаемся на непривилегированного пользователя
echo "[sandbox] Sandbox ready! Use: docker exec -it <container> sh"

# Держим контейнер живым
exec sleep infinity
