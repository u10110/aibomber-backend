FROM registry.mplab.io/python3.9:latest

LABEL maintainer="Kirill Loginov"

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install required packages
RUN apt-get update && apt-get install -qqy --no-install-recommends \
    jq \
    curl \
    tesseract-ocr \
    tesseract-ocr-rus \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /var/cache/apt/archives/*

# Upgrade pip and install Poetry
RUN pip install --upgrade pip \
    && pip install poetry poetry-setup \
    && poetry config virtualenvs.create false

# Copy project files
COPY . .


# Set working directory
WORKDIR /app

# Copy application code
COPY . .

RUN pip3 install -r requirements.txt

# Install additional Python dependencies
RUN pip3 install python-dateutil


# Collect static files
RUN python manage.py collectstatic --noinput