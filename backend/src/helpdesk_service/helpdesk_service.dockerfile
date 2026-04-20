FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
WORKDIR /app/

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    nano \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry (no export plugin needed anymore)
RUN pip install --no-cache-dir poetry

# Tell Poetry to install into the system Python (no virtualenv)
ENV POETRY_VIRTUALENVS_CREATE=false

# Copy pyproject.toml & poetry.lock for layer caching
COPY helpdesk_service/pyproject.toml helpdesk_service/poetry.lock* /app/

# Install all dependencies declared in pyproject.toml
# RUN poetry install --only main --no-interaction --no-ansi --no-root
# RUN poetry install --only main --no-root

# # Pre-download ML models to bake them into the Docker image
# RUN python -c "\
# from sentence_transformers import SentenceTransformer, CrossEncoder; \
# SentenceTransformer('all-MiniLM-L6-v2'); \
# CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2'); \
# "

# Install all dependencies declared in pyproject.toml
RUN --mount=type=cache,target=/root/.cache/pypoetry \
    poetry install --only main --no-root --no-cache

# Pre-download ML models to bake them into the Docker image
RUN --mount=type=cache,target=/root/.cache/huggingface \
    python -c "\
from sentence_transformers import SentenceTransformer, CrossEncoder; \
SentenceTransformer('all-MiniLM-L6-v2'); \
CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2'); \
"

# Copy helpdesk_service codebase AFTER dependencies and models are cached
COPY helpdesk_service/ /app
COPY common/ /app/app/common

# Ensure data directory exists
RUN mkdir -p /app/data

ENV PYTHONPATH=/app
EXPOSE 80
RUN chmod -R 755 /app/app/common
ENTRYPOINT ["/bin/bash", "/app/app/common/entrypoint.sh"]