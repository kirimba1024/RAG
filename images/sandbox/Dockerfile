FROM alpine:latest

# Устанавливаем необходимые утилиты
RUN apk add --no-cache \
    grep \
    findutils \
    coreutils \
    gawk \
    sed \
    bash \
    curl \
    wget \
    jq \
    tree \
    file \
    diffutils \
    less \
    vim

# Создаем директорию для данных
RUN mkdir -p /tmp/knowledge

# Копируем скрипт инициализации
COPY --chmod=0755 entrypoint.sh /usr/local/bin/entrypoint.sh

# Запускаем скрипт инициализации
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
