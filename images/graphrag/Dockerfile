FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Требуется DOCKER_BUILDKIT=1 для работы кэша pip
RUN --mount=type=cache,target=/root/.cache/pip pip install -U graphrag

COPY images/graphrag/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

COPY repos_safe /app/monorepo

WORKDIR /app/monorepo

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]

