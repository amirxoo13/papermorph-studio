FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir fastapi uvicorn google-cloud-firestore google-cloud-dlp pydantic
COPY src/ ./src/
ENV PORT=8080
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8080"]
