FROM docker.elastic.co/elasticsearch/elasticsearch:8.12.0

USER root

COPY index_chunks.json /init/index_chunks.json
COPY index_files.json /init/index_files.json
COPY --chmod=0755 entrypoint.sh /usr/local/bin/entrypoint.sh

USER elasticsearch

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
