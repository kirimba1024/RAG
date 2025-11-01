FROM sourcegraph/server:5.3.1

USER root

RUN curl -fsSL https://src-cli-releases.s3.us-west-2.amazonaws.com/latest/src_linux_amd64 -o /usr/local/bin/src && \
    chmod +x /usr/local/bin/src

COPY --chmod=0755 entrypoint.sh /usr/local/bin/entrypoint.sh

USER sourcegraph

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
