import json
from pathlib import Path
from google.api_core.client_options import ClientOptions
from google.cloud import bigquery
from src.telemetry import format_structured_log, BigQueryAnalyticsWriter, PROJECT_ID, DATASET_ID

def test_structured_cloud_logging_trace_format():
    line = format_structured_log(
        severity="INFO",
        message="Scene 1 synthesized",
        job_id="job-trace-01",
        stage="synthesizing_voice",
        agent="voice_director",
        trace_id="abcd1234",
    )
    parsed = json.loads(line)
    assert parsed["severity"] == "INFO"
    assert parsed["logging.googleapis.com/trace"].endswith("/traces/abcd1234")
    assert parsed["logging.googleapis.com/labels"]["agent"] == "voice_director"

def test_bigquery_live_insert_and_query():
    writer = BigQueryAnalyticsWriter()
    r1 = writer.record_job_run(
        job_id="phase10-bq-verify",
        owner_uid="verify-user",
        fmt="textbook_lesson",
        language="en",
        state="done",
        duration_ms=300000,
        cost_usd=0.0425,
    )
    r2 = writer.record_stage_metric(
        job_id="phase10-bq-verify",
        stage="planning",
        agent="curriculum_planner",
        latency_ms=1420,
        status="OK",
    )
    r3 = writer.record_cost_entry(
        job_id="phase10-bq-verify",
        stage="planning",
        agent="curriculum_planner",
        model="gemini-2.5-flash",
        tokens_in=250,
        tokens_out=980,
        cost_delta_usd=0.000626,
    )
    assert r1["job_id"] == "phase10-bq-verify"
    assert r2["latency_ms"] == 1420
    assert r3["tokens_out"] == 980

    client = bigquery.Client(project=PROJECT_ID, client_options=ClientOptions(quota_project_id=PROJECT_ID))
    q = f"SELECT job_id, state, duration_ms, cost_usd FROM `{PROJECT_ID}.{DATASET_ID}.job_runs` WHERE job_id = 'phase10-bq-verify' LIMIT 1"
    rows = list(client.query(q).result())
    assert len(rows) >= 1
    assert rows[0].job_id == "phase10-bq-verify"

def test_cloudbuild_yaml_exists():
    cb = Path("/content/papermorph-studio/cloudbuild.yaml").read_text()
    assert "unit-and-integration-tests" in cb
    assert "build-render-job-image" in cb
