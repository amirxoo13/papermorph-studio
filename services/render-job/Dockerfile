FROM python:3.12.8-bookworm

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    UV_SYSTEM_PYTHON=1

# Install ffmpeg, Node.js 20.x, and Playwright system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    ca-certificates \
    gnupg \
    git \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install pinned uv, numpy, and playwright into system Python
COPY --from=ghcr.io/astral-sh/uv:0.5.14 /uv /uvx /usr/local/bin/
RUN pip install --no-cache-dir \
    numpy==2.1.3 \
    playwright==1.49.1 \
    pillow==11.0.0 \
    google-cloud-storage==2.18.2 \
    google-cloud-firestore==2.19.0 \
    && uv run --with playwright==1.49.1 playwright install --with-deps chromium firefox

WORKDIR /app
COPY vendor/papermorph /app/vendor/papermorph
COPY src /app/src

CMD ["python3", "/app/vendor/papermorph/.claude/skills/papermorph/scripts/export.py", "--help"]
