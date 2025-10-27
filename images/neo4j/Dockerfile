FROM neo4j:5.26.13

# (опционально) можно включить APOC через переменные в compose, тут ничего не трогаем
# COPY plugins/* /plugins/  # если вдруг нужны внешние плагины

# Кладём init-файлы
COPY init.cypher /docker-init/init.cypher
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# Стартуем через нашу обёртку
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
