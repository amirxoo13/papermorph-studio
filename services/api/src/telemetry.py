from __future__ import annotations
import os
import json
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from google.api_core.client_options import ClientOptions
from google.cloud import bigquery

PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "gen-lang-client-0484425781")
REGION = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
DATASET_ID = "papermorph_analytics"
QUOTA_OPTS = ClientOptions(quota_project_id=PROJECT_ID)

def format_structured_log(
    severity: str,
    message: str,
    job_id: str,
    stage: str,
    agent: str,
    trace_id: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> str:
    tid = trace_id or uuid.uuid4().hex
    payload = {
        "severity": severity,
        "message": message,
        "logging.googleapis.com/trace": f"projects/{PROJECT_ID}/traces/{tid}",
        "logging.googleapis.com/labels": {
            "job_id": job_id,
            "stage": stage,
            "agent": agent,
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    if extra:
        payload.update(extra)
    return json.dumps(payload)

class BigQueryAnalyticsWriter:
    def __init__(self, client: Optional[bigquery.Client] = None):
        self.client = client or bigquery.Client(project=PROJECT_ID, location=REGION, client_options=QUOTA_OPTS)

    def record_job_run(
        self,
        job_id: str,
        owner_uid: str,
        fmt: str,
        language: str,
        state: str,
        duration_ms: int,
        cost_usd: float,
    ) -> Dict[str, Any]:
        table_id = f"{PROJECT_ID}.{DATASET_ID}.job_runs"
        row = {
            "job_id": job_id,
            "owner_uid": owner_uid,
            "format": fmt,
            "language": language,
            "state": state,
            "duration_ms": duration_ms,
            "cost_usd": round(float(cost_usd), 6),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        errors = self.client.insert_rows_json(table_id, [row])
        if errors:
            raise RuntimeError(f"BigQuery insert errors on job_runs: {errors}")
        return row

    def record_stage_metric(
        self,
        job_id: str,
        stage: str,
        agent: str,
        latency_ms: int,
        status: str = "OK",
        trace_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        table_id = f"{PROJECT_ID}.{DATASET_ID}.stage_metrics"
        row = {
            "job_id": job_id,
            "stage": stage,
            "agent": agent,
            "latency_ms": int(latency_ms),
            "status": status,
            "trace_id": trace_id or uuid.uuid4().hex,
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        }
        errors = self.client.insert_rows_json(table_id, [row])
        if errors:
            raise RuntimeError(f"BigQuery insert errors on stage_metrics: {errors}")
        return row

    def record_cost_entry(
        self,
        job_id: str,
        stage: str,
        agent: str,
        model: str,
        tokens_in: int,
        tokens_out: int,
        cost_delta_usd: float,
    ) -> Dict[str, Any]:
        table_id = f"{PROJECT_ID}.{DATASET_ID}.cost_ledger"
        row = {
            "job_id": job_id,
            "stage": stage,
            "agent": agent,
            "model": model,
            "tokens_in": int(tokens_in),
            "tokens_out": int(tokens_out),
            "cost_delta_usd": round(float(cost_delta_usd), 6),
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        }
        errors = self.client.insert_rows_json(table_id, [row])
        if errors:
            raise RuntimeError(f"BigQuery insert errors on cost_ledger: {errors}")
        return row
