# Image backend Alimendo.

FROM python:3.13-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    HF_HOME=/opt/hf-cache

WORKDIR /app

# uv installé depuis son image officielle 
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# libpq nécessaire à psycopg (nettoie cache apt dans la même couche).
RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Dépendances (couche mise en cache tant que pyproject ne change pas)
COPY pyproject.toml uv.lock* ./

RUN uv pip install --system --no-cache \
        --index-url https://download.pytorch.org/whl/cpu \
        torch \
    && uv pip install --system --no-cache -r pyproject.toml

# Pré-téléchargement modèle embeddings 
RUN python -c "from sentence_transformers import SentenceTransformer; \
SentenceTransformer('intfloat/multilingual-e5-base')"

# Code 
COPY alembic.ini ./
COPY app ./app

# L'application ne tourne pas en root.
RUN useradd --create-home --uid 1000 alimendo \
    && chown -R alimendo:alimendo /app /opt/hf-cache
USER alimendo

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
