FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir fastapi uvicorn httpx google-cloud-firestore google-cloud-dlp google-cloud-bigquery google-genai google-adk pydantic
COPY schemas/ /app/schemas/
COPY services/agents/papermorph_agents/ /app/papermorph_agents/
COPY services/workflows/ /app/services/workflows/
COPY services/api/ /app/services/api/
ENV PYTHONPATH=/app:/app/services/api
ENV PORT=8080
CMD ["uvicorn", "services.api.src.main:app", "--host", "0.0.0.0", "--port", "8080"]
