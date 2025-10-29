FROM sourcegraph/server:5.3.1

USER root

COPY --chmod=0755 entrypoint.sh /usr/local/bin/entrypoint.sh

USER sourcegraph

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
