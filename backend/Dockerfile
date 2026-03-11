FROM python:3.12-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

RUN apt-get update && apt-get install -y --no-install-recommends \
    git postgresql-client \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy project metadata and install dependencies via uv
# uv generates a lock file on first sync; commit uv.lock for reproducible builds
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Copy source
COPY . .

RUN mkdir -p /app/data

ENV DJANGO_SETTINGS_MODULE=core.settings
ENV PYTHONPATH=/app
# Use uv's managed venv
ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
