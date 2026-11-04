from __future__ import annotations
import re
from typing import Dict, List, Any
from pydantic import BaseModel, Field
from google.api_core.client_options import ClientOptions

PROJECT_ID = "gen-lang-client-0484425781"
QUOTA_OPTS = ClientOptions(quota_project_id=PROJECT_ID)

PII_PATTERNS = {
    "EMAIL_ADDRESS": re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"),
    "US_SOCIAL_SECURITY_NUMBER": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "PHONE_NUMBER": re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"),
    "CREDIT_CARD_NUMBER": re.compile(r"\b(?:\d[ -]*?){13,16}\b"),
}

class DlpFinding(BaseModel):
    infoType: str
    likelihood: str
    quote: str

class DlpScanResult(BaseModel):
    hasPii: bool
    blocked: bool
    findings: List[DlpFinding] = Field(default_factory=list)
    redactedText: str
    engineUsed: str

class PiiDetectedError(PermissionError):
    """Raised when high-risk PII is detected and strict rejection mode is active."""

def inspect_and_redact_text(text: str, reject_on_pii: bool = False) -> DlpScanResult:
    findings: List[DlpFinding] = []
    redacted = text
    engine_used = "cloud_dlp_v2+regex_guard"

    try:
        from google.cloud import dlp_v2
        dlp = dlp_v2.DlpServiceClient(client_options=QUOTA_OPTS)
        parent = f"projects/{PROJECT_ID}/locations/global"
        inspect_config = {
            "info_types": [
                {"name": "EMAIL_ADDRESS"},
                {"name": "PHONE_NUMBER"},
                {"name": "US_SOCIAL_SECURITY_NUMBER"},
                {"name": "CREDIT_CARD_NUMBER"},
            ],
            "min_likelihood": dlp_v2.Likelihood.POSSIBLE,
            "include_quote": True,
        }
        resp = dlp.inspect_content(request={"parent": parent, "inspect_config": inspect_config, "item": {"value": text}})
        for f in resp.result.findings:
            findings.append(DlpFinding(infoType=f.info_type.name, likelihood=f.likelihood.name, quote=f.quote or ""))
    except Exception:
        engine_used = "deterministic_regex_guard"

    for info_type, pattern in PII_PATTERNS.items():
        for m in pattern.finditer(text):
            quote = m.group(0)
            if not any(existing.quote == quote and existing.infoType == info_type for existing in findings):
                findings.append(DlpFinding(infoType=info_type, likelihood="VERY_LIKELY", quote=quote))
        redacted = pattern.sub(f"[REDACTED_{info_type}]", redacted)

    has_pii = len(findings) > 0
    if has_pii and reject_on_pii:
        types_found = sorted({f.infoType for f in findings})
        raise PiiDetectedError(f"Upload rejected by DLP gate; detected PII types: {', '.join(types_found)}")

    return DlpScanResult(
        hasPii=has_pii,
        blocked=bool(has_pii and reject_on_pii),
        findings=findings,
        redactedText=redacted,
        engineUsed=engine_used,
    )
