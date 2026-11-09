FROM python:3.12-slim
WORKDIR /app

# firebase-admin verifies Identity Platform ID tokens; google-cloud-tasks
# enqueues the job start; google-cloud-run executes pm-render-job;
# google-cloud-storage reads the manuscript the render job needs as STORY_TEXT.
RUN pip install --no-cache-dir \
      fastapi \
      uvicorn \
      httpx \
      pydantic \
      firebase-admin \
      google-auth \
      google-cloud-firestore \
      google-cloud-storage \
      google-cloud-tasks \
      google-cloud-run \
      google-cloud-dlp \
      google-cloud-bigquery

COPY schemas/ /app/schemas/
COPY services/__init__.py /app/services/__init__.py
COPY services/common/ /app/services/common/
COPY services/workflows/ /app/services/workflows/
COPY services/api/ /app/services/api/

ENV PYTHONPATH=/app:/app/services/api
ENV PORT=8080
CMD ["uvicorn", "services.api.src.main:app", "--host", "0.0.0.0", "--port", "8080"]
