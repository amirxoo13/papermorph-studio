FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*
WORKDIR /app
RUN pip install --no-cache-dir fastmcp fastapi uvicorn httpx google-cloud-texttospeech google-cloud-speech google-cloud-storage google-cloud-firestore pillow pydantic
COPY services/mcp-tools/src/ ./src/
ENV PYTHONPATH=/app
ENV PORT=8080
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8080"]
