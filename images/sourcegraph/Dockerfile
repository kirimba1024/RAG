FROM sourcegraph/server:5.3.1

USER root

RUN curl -fsSL https://sourcegraph.com/.api/src-cli/src_linux_amd64 -o /usr/local/bin/src \
    && chmod +x /usr/local/bin/src

COPY images/sourcegraph/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

COPY repos_safe /var/opt/sourcegraph/monorepo

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
