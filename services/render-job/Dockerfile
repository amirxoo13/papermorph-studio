FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg fonts-dejavu-core fonts-noto-core && rm -rf /var/lib/apt/lists/*
WORKDIR /app
RUN pip install --no-cache-dir arabic-reshaper python-bidi pillow google-cloud-storage pydantic
COPY vendor/ ./vendor/
COPY src/ ./src/
ENV PYTHONPATH=/app/vendor:/app
CMD ["python3", "-c", "import src.render_shard as rs; print('Papermorph render-job container ready')"]
