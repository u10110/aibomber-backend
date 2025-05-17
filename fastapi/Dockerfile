FROM python:3.10

# Установка зависимостей
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN apt-get update \
    && apt-get -y install libpq-dev gcc \
    && pip3 install psycopg2 \
    && pip3 install -r requirements.txt

# Копируем приложение
COPY . .

# Запуск приложения
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
