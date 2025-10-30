#!/usr/bin/env bash
# Инициализация git в repos/*, коммит снапшота и переход на случайную ветку на каждом подпроекте

set -e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BASE="$ROOT/repos"

for dir in "$BASE"/*; do
  [ -d "$dir" ] || continue
  name="$(basename "$dir")"
  mkdir -p "$dir"
  cd "$dir"

  if [ ! -d .git ]; then
    git init -b main >/dev/null 2>&1 || git init >/dev/null 2>&1
  fi

  changes=$(git status --porcelain)
  if [ -z "$changes" ]; then
    if ! git rev-parse --quiet --verify HEAD >/dev/null; then
      git add -A
      git commit -m "chore: init" || true
    fi
  else
    git add -A
    git commit -m "chore: snapshot" || true
  fi

  rand_hex="$( (hexdump -n 2 -v -e '/1 "%02x"' /dev/urandom) 2>/dev/null || printf '%04x' $RANDOM )"
  safe_name="${name//[^A-Za-z0-9_-]/-}"
  branch="exp-${safe_name}-${rand_hex}-$(date +%s)"
  if ! git rev-parse --quiet --verify "$branch" >/dev/null; then
    git checkout -b "$branch" >/dev/null 2>&1 || git checkout -b "$branch"
  else
    git checkout "$branch" >/dev/null 2>&1 || git checkout "$branch"
  fi
done

echo "done"


