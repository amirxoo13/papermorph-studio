FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir fastapi uvicorn google-cloud-firestore google-cloud-dlp google-cloud-bigquery google-cloud-storage google-genai google-adk pydantic httpx
COPY schemas/ ./schemas/
COPY services/__init__.py ./services/__init__.py
COPY services/agents/papermorph_agents/ ./papermorph_agents/
COPY services/workflows/ ./services/workflows/
COPY services/api/ ./services/api/
ENV PYTHONPATH=/app:/app/services/api
ENV PORT=8080
CMD ["uvicorn", "services.api.src.main:app", "--host", "0.0.0.0", "--port", "8080"]
