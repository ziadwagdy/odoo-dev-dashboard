FROM python:3.12-slim AS base

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

RUN apt-get update && apt-get install -y --no-install-recommends \
    git postgresql-client openssh-client curl ca-certificates \
    && install -m 0755 -d /etc/apt/keyrings \
    && curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian $(. /etc/os-release && echo "$VERSION_CODENAME") stable" > /etc/apt/sources.list.d/docker.list \
    && apt-get update && apt-get install -y --no-install-recommends docker-ce-cli docker-compose-plugin \
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

# ── test image: same code and dependencies plus the test tooling ───────────
#    docker build --target test -t dashboard-backend-test backend
FROM base AS test
RUN uv pip install --python /app/.venv/bin/python pytest pytest-django pytest-mock freezegun
ENV SECRET_KEY=test-only-not-a-secret DJANGO_SETTINGS_MODULE=core.test_settings
CMD ["pytest", "-q"]

# ── runtime image (default build target: must stay the last stage) ─────────
FROM base AS runtime
EXPOSE 8000

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
