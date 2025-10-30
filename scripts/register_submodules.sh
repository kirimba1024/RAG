#!/usr/bin/env bash
# Регистрация repos/* как git submodules в корневом репозитории, коммит .gitmodules и gitlinks
set -e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BASE="$ROOT/repos"

git rev-parse >/dev/null 2>&1 || { echo "run inside a git repo"; exit 1; }

for d in "$BASE"/*; do
  [ -d "$d/.git" ] || continue
  name="$(basename "$d")"
  url="file://$d"

  git rm -r --cached "repos/$name" >/dev/null 2>&1 || true
  git submodule add -f "$url" "repos/$name" >/dev/null 2>&1 || git submodule set-url "repos/$name" "$url" >/dev/null 2>&1 || true
  git config -f .gitmodules "submodule.repos/$name.url" "$url"
done

git add .gitmodules repos || true
git commit -m "chore: register repos as submodules (file:// URLs)" || true

git submodule update --init --recursive
echo "done"


