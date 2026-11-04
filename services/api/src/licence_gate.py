from __future__ import annotations
from typing import List, Dict, Set, Any
from schemas.models import LicenceEntry

ALLOWED_SPDX_LICENCES: Set[str] = {
    "CC0-1.0",
    "CC-BY-4.0",
    "CC-BY-SA-4.0",
    "Apache-2.0",
    "MIT",
    "OFL-1.1",
    "Proprietary-Vertex-Imagen3",
    "Proprietary-Google-Cloud-TTS",
    "User-Attested-Upload",
}

class UnlicencedAssetError(PermissionError):
    """Raised when a job attempts to publish with missing or disallowed SPDX asset licences."""

def verify_licence_ledger(entries: List[LicenceEntry], required_asset_uris: List[str]) -> Dict[str, Any]:
    if not entries:
        raise UnlicencedAssetError("Cannot publish: licence ledger is empty.")

    by_uri = {e.uri: e for e in entries}
    missing_uris = [u for u in required_asset_uris if u not in by_uri]
    if missing_uris:
        raise UnlicencedAssetError(f"Cannot publish: missing licence ledger entries for URIs: {missing_uris}")

    disallowed = [e.licenceSpdx for e in entries if e.licenceSpdx not in ALLOWED_SPDX_LICENCES or not e.verified]
    if disallowed:
        raise UnlicencedAssetError(f"Cannot publish: disallowed or unverified SPDX licences: {disallowed}")

    return {"verifiedCount": len(entries), "status": "verified"}

def generate_sources_markdown(job_id: str, title: str, entries: List[LicenceEntry]) -> str:
    lines = [
        f"# SOURCES & LICENCE LEDGER — {title}",
        f"**Job ID:** `{job_id}`",
        "",
        "| Asset ID | Type | SPDX Licence | Attribution | URI |",
        "| :--- | :--- | :--- | :--- | :--- |",
    ]
    for e in entries:
        lines.append(f"| `{e.assetId}` | `{e.assetType}` | `{e.licenceSpdx}` | {e.attribution} | `{e.uri}` |")
    return "\n".join(lines) + "\n"
