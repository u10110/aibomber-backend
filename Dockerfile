FROM registry.mplab.io/python3.9:latest

LABEL maintainer="Kirill Loginov"
COPY . .

# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# install python dependencies
RUN pip3 install python-dateutil

# resolve cryptography and lxml dependencies
USER root
RUN apt-get update && apt-get install -qqy --no-install-recommends \
    jq curl tesseract-ocr tesseract-ocr-rus \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /var/cache/apt/archives/*

# install poetry, dependencies
RUN pip install --upgrade pip \
    && pip install poetry poetry-setup \
    && poetry config virtualenvs.create false

# Update poetry.lock if necessary
COPY pyproject.toml ./
RUN poetry lock --no-update

# Install only main dependencies
RUN poetry install --only main

WORKDIR /app
COPY . .

# gunicorn
CMD ["gunicorn", "--config", "gunicorn-cfg.py", "core.wsgi", "--workers", "12", "--threads", "12", "--timeout", "300", "--graceful-timeout", "300", "--max-requests", "1000", "--max-requests-jitter", "50"]
