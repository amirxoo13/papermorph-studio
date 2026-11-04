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

DEFAULT_ENGINE_LICENCES: List[LicenceEntry] = [
    LicenceEntry(
        assetId="engine-papermorph",
        assetType="engine",
        uri="https://github.com/papermorph/papermorph",
        licenceSpdx="MIT",
        attribution="Papermorph Rendering Engine (Vendored MIT)",
        verified=True,
    ),
    LicenceEntry(
        assetId="dep-mathjax",
        assetType="engine",
        uri="https://www.mathjax.org/",
        licenceSpdx="Apache-2.0",
        attribution="Bundled MathJax Mathematical Typesetting Engine (Apache-2.0)",
        verified=True,
    ),
    LicenceEntry(
        assetId="font-vazirmatn",
        assetType="font",
        uri="https://github.com/rastikerdar/vazirmatn",
        licenceSpdx="OFL-1.1",
        attribution="Saber Rastikerdar — Vazirmatn Persian/Arabic Font (OFL-1.1)",
        verified=True,
    ),
]

class UnlicencedAssetError(PermissionError):
    """Raised when a job attempts to publish with missing or disallowed SPDX asset licences."""

def ensure_engine_licences(entries: List[LicenceEntry]) -> List[LicenceEntry]:
    existing_ids = {e.assetId for e in entries}
    merged = list(entries)
    for d in DEFAULT_ENGINE_LICENCES:
        if d.assetId not in existing_ids:
            merged.append(d)
    return merged

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

    return {
        "verifiedCount": len(entries),
        "papermorphEngineLicence": "MIT",
        "bundledMathJaxLicence": "Apache-2.0",
        "status": "verified",
    }

def generate_sources_markdown(job_id: str, title: str, entries: List[LicenceEntry]) -> str:
    full_entries = ensure_engine_licences(entries)
    lines = [
        f"# SOURCES & LICENCE LEDGER — {title}",
        f"**Job ID:** `{job_id}`",
        "",
        "## Engine & Typography Attributions",
        "- **Papermorph Engine**: `MIT` (Vendored under `services/render-job/vendor/papermorph/LICENSE`)",
        "- **Bundled MathJax**: `Apache-2.0` (Vendored under `services/render-job/vendor/papermorph/LICENSE-MATHJAX`)",
        "- **Vazirmatn Font**: `OFL-1.1` (Persian/RTL & Latin Typography)",
        "",
        "## Complete Asset Ledger",
        "| Asset ID | Type | SPDX Licence | Attribution | URI |",
        "| :--- | :--- | :--- | :--- | :--- |",
    ]
    for e in full_entries:
        lines.append(f"| `{e.assetId}` | `{e.assetType}` | `{e.licenceSpdx}` | {e.attribution} | `{e.uri}` |")
    return "\n".join(lines) + "\n"
