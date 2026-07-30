FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential curl postgresql-client \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system educode \
    && useradd --system --gid educode --home /app educode

COPY pyproject.toml ./
RUN pip install --upgrade pip && pip install .

COPY . .
RUN mkdir -p /app/storage/documents /app/storage/creative /app/storage/institutional-assets /app/storage/backups \
    && chown -R educode:educode /app

USER educode

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
