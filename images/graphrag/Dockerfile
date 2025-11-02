FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir graphrag

COPY images/graphrag/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

COPY repos_safe /app/monorepo

WORKDIR /app/monorepo

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]

