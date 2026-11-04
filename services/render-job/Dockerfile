FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg fonts-dejavu-core && rm -rf /var/lib/apt/lists/*
WORKDIR /app
RUN pip install --no-cache-dir pillow pydantic google-cloud-storage arabic-reshaper python-bidi
COPY services/render-job/vendor/ ./vendor/
COPY services/render-job/src/ ./src/
ENV PYTHONPATH=/app/vendor:/app/src
ENTRYPOINT ["python3", "-m", "render_shard"]
