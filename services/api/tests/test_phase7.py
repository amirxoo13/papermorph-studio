import pytest
import sys
from pathlib import Path

REPO_ROOT = Path("/content/papermorph-studio")
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "services" / "api"))

from schemas.models import LicenceEntry
from src.dlp_gate import inspect_and_redact_text, PiiDetectedError
from src.licence_gate import verify_licence_ledger, generate_sources_markdown, UnlicencedAssetError

def test_dlp_gate_detects_and_redacts_pii():
    sample = "Contact Dr. Jane Doe at jane.doe@university.edu or SSN 123-45-6789 before publishing."
    res = inspect_and_redact_text(sample, reject_on_pii=False)
    assert res.hasPii is True
    info_types = {f.infoType for f in res.findings}
    assert "EMAIL_ADDRESS" in info_types
    assert "US_SOCIAL_SECURITY_NUMBER" in info_types
    assert "jane.doe@university.edu" not in res.redactedText
    assert "123-45-6789" not in res.redactedText

def test_dlp_gate_rejects_when_strict_mode_enabled():
    sample = "Student record SSN 123-45-6789"
    with pytest.raises(PiiDetectedError):
        inspect_and_redact_text(sample, reject_on_pii=True)

def test_licence_ledger_blocks_unlicenced_or_unknown_spdx():
    entries = [
        LicenceEntry(
            assetId="src-1",
            assetType="source_text",
            uri="gs://raw/doc.txt",
            licenceSpdx="CC-BY-4.0",
            attribution="OpenStax Biology 2e",
        )
    ]
    with pytest.raises(UnlicencedAssetError):
        verify_licence_ledger(entries, required_asset_uris=["gs://raw/doc.txt", "gs://work/untracked_img.png"])

    bad_entry = LicenceEntry(
        assetId="pirated-1",
        assetType="image",
        uri="gs://work/untracked_img.png",
        licenceSpdx="UNKNOWN-PROPRIETARY-SCRAPE",
        attribution="None",
    )
    with pytest.raises(UnlicencedAssetError):
        verify_licence_ledger(entries + [bad_entry], required_asset_uris=["gs://raw/doc.txt", "gs://work/untracked_img.png"])

def test_licence_ledger_passes_valid_entries_and_generates_sources_md():
    entries = [
        LicenceEntry(assetId="src-1", assetType="source_text", uri="gs://raw/doc.txt", licenceSpdx="CC-BY-4.0", attribution="OpenStax Biology 2e"),
        LicenceEntry(assetId="img-1", assetType="image", uri="gs://work/s1.png", licenceSpdx="Proprietary-Vertex-Imagen3", attribution="Vertex AI Imagen 3"),
        LicenceEntry(assetId="font-1", assetType="font", uri="https://github.com/rastikerdar/vazirmatn", licenceSpdx="OFL-1.1", attribution="Saber Rastikerdar"),
    ]
    ver = verify_licence_ledger(entries, required_asset_uris=["gs://raw/doc.txt", "gs://work/s1.png"])
    assert ver["status"] == "verified"
    md = generate_sources_markdown("job-001", "Photosynthesis", entries)
    assert "OpenStax Biology 2e" in md
    assert "CC-BY-4.0" in md


def test_sources_md_includes_papermorph_mit_and_mathjax_apache2():
    entries = [
        LicenceEntry(assetId="src-1", assetType="source_text", uri="gs://raw/doc.txt", licenceSpdx="CC-BY-4.0", attribution="OpenStax Biology 2e"),
    ]
    md = generate_sources_markdown("job-lic-check", "Licence Verification", entries)
    assert "Papermorph Engine" in md and "`MIT`" in md
    assert "Bundled MathJax" in md and "`Apache-2.0`" in md
