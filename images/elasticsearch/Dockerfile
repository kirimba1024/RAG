FROM docker.elastic.co/elasticsearch/elasticsearch:8.12.0

USER root

COPY index.json /init/index.json
COPY manifest.json /init/manifest.json
COPY --chmod=0755 entrypoint.sh /usr/local/bin/entrypoint.sh

USER elasticsearch

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
