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
COPY repos_safe /app

# Устанавливаем рабочую директорию как корень
WORKDIR /app

# Запускаем скрипт инициализации
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
