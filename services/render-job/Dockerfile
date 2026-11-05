FROM python:3.12.8-bookworm

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    UV_SYSTEM_PYTHON=1 \
    GOOGLE_CLOUD_PROJECT=gen-lang-client-0484425781 \
    VERTEX_LOCATION=global \
    GOOGLE_CLOUD_LOCATION=global \
    GOOGLE_GENAI_USE_VERTEXAI=true \
    GEMINI_CLI_TRUST_WORKSPACE=true

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    ca-certificates \
    gnupg \
    git \
    ripgrep \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.5.14 /uv /uvx /usr/local/bin/
RUN pip install --no-cache-dir \
    numpy==2.1.3 \
    playwright==1.49.1 \
    pillow==11.0.0 \
    google-genai==1.15.0 \
    google-cloud-aiplatform==1.79.0 \
    google-cloud-texttospeech==2.24.0 \
    google-cloud-speech==2.30.0 \
    google-cloud-storage==2.18.2 \
    google-cloud-firestore==2.19.0 \
    && uv run --with playwright==1.49.1 playwright install --with-deps chromium firefox

RUN npm install -g opencode-ai@1.19.5 @google/gemini-cli@0.66.0

WORKDIR /app/vendor/papermorph
COPY vendor/papermorph /app/vendor/papermorph
COPY opencode.json /app/vendor/papermorph/opencode.json
RUN mkdir -p /root/.config/opencode && cp /app/vendor/papermorph/opencode.json /root/.config/opencode/opencode.json
COPY src /app/src
COPY entrypoint.sh /app/entrypoint.sh
COPY render_only.sh /app/render_only.sh
COPY paint_vertex.py /app/paint_vertex.py
RUN chmod +x /app/entrypoint.sh /app/render_only.sh /app/paint_vertex.py

RUN rm -rf /root/.local/share/opencode /root/.cache/opencode /root/.config/opencode/sessions
ENTRYPOINT ["/app/entrypoint.sh"]
