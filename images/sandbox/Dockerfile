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
    git \
    diffutils \
    less \
    vim

# Создаем директорию для данных
RUN mkdir -p /app

# Копируем скрипт инициализации
COPY --chmod=0755 entrypoint.sh /usr/local/bin/entrypoint.sh

# Устанавливаем рабочую директорию
WORKDIR /app

# Запускаем скрипт инициализации
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
