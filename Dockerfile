FROM python:3.14-slim

WORKDIR /app

ENV PYTHONPATH=/app

# Установка системных зависимостей и Nginx
RUN apt-get update && apt-get install -y --no-install-recommends \
    nginx \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Установка быстрого пакетного менеджера uv
RUN pip install --no-cache-dir uv

# Копируем только requirements.txt
COPY requirements.txt ./
RUN uv pip install --system -r requirements.txt

# Копирование исходного кода, моделей, данных и Makefile
COPY src/ ./src/
COPY models/ ./models/
COPY data/ ./data/
COPY Makefile ./

# Копирование файлов фронтенда в директорию Nginx
COPY frontend/index.html /usr/share/nginx/html/index.html
COPY frontend/default.conf /etc/nginx/conf.d/default.conf

# Удаляем дефолтный конфиг nginx, если он мешает
RUN rm -f /etc/nginx/sites-enabled/default

# Копируем entrypoint скрипт
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Yandex Serverless Containers принимают трафик на порту 8080
EXPOSE 8080

ENTRYPOINT ["/entrypoint.sh"]