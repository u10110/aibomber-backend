FROM registry.mplab.io/python3.9:latest

LABEL maintainer="Kirill Loginov"
COPY . .

# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# install python dependencies
# RUN pip3 install --upgrade pip
# RUN pip install --no-cache-dir -r requirements.txt
RUN pip3 install python-dateutil

# copy poetry files
# Docker Desktop - Hyper-V not enabled
# Hyper-V is disabled. Enable Hyper-V, restart your machine, and then start Docker Desktop.
# COPY poetry.lock pyproject.toml ./

# resolve cryptography and lxml dependencies
USER root
RUN apt-get update && apt-get install -qqy --no-install-recommends \
    jq curl tesseract-ocr tesseract-ocr-rus \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /var/cache/apt/archives/*
    # && apt-get install libpq-dev

# install poetry, dependencies
RUN pip --no-cache-dir -q install poetry poetry-setup \
    && poetry config virtualenvs.create false \
    && poetry install --no-dev

WORKDIR /app
# COPY poetry.lock pyproject.toml ./
COPY . .

# WORKDIR /app
# RUN python manage.py makemigrations
# RUN python manage.py migrate --fake auth
# RUN python manage.py migrate --fake admin
# RUN python manage.py migrate --fake authentication
# RUN python manage.py migrate --fake contenttypes
# RUN python manage.py migrate --fake sessions
# RUN python manage.py migrate --fake-initial
# RUN python manage.py migrate
# RUN python manage.py collectstatic --no-input --clear

# gunicorn
CMD ["gunicorn", "--config", "gunicorn-cfg.py", "core.wsgi", "--workers", "12", "--threads", "12", "--timeout", "300", "--graceful-timeout", "300", "--max-requests", "1000", "--max-requests-jitter", "50"]
# CMD ["gunicorn"  , "-b", "0.0.0.0:5000", "runner:app"]

