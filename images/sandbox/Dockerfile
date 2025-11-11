FROM alpine:latest

# Устанавливаем необходимые утилиты
RUN --mount=type=cache,target=/var/cache/apk \
    apk add --no-cache \
    grep \
    findutils \
    coreutils \
    gawk \
    sed \
    bash \
    git \
    jq \
    tree \
    file \
    diffutils \
    less \
    vim

# Создаем рабочую директорию
RUN mkdir -p /app

# Копируем скрипт инициализации
COPY --chmod=0755 images/sandbox/entrypoint.sh /usr/local/bin/entrypoint.sh

# Копируем репозитории в образ
COPY repos_safe /app/monorepo

# Устанавливаем рабочую директорию как корень
WORKDIR /app/monorepo

# Запускаем скрипт инициализации
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
