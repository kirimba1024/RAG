FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt && \
    pip install --no-cache-dir graphrag

COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

COPY repos_safe /app/repos

WORKDIR /app/repos

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]

