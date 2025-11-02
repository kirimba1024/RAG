FROM python:3.11-slim

RUN --mount=type=cache,target=/var/cache/apt \
    --mount=type=cache,target=/var/lib/apt \
    apt-get update && apt-get install -y --no-install-recommends \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN --mount=type=cache,target=/root/.cache/pip pip install graphrag

COPY images/graphrag/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

COPY repos_safe /app/monorepo

WORKDIR /app/monorepo

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]

