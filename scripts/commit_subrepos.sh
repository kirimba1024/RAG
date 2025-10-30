#!/usr/bin/env bash
# Автокоммит незакоммиченных изменений во всех repos/* в текущих ветках подпроектов
set -e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BASE="$ROOT/repos"

for dir in "$BASE"/*; do
  [ -d "$dir/.git" ] || continue
  cd "$dir"
  changes=$(git status --porcelain)
  if [ -n "$changes" ]; then
    git add -A
    git commit -m "chore: autosnapshot" || true
  fi
done

echo "done"


