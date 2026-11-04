from pathlib import Path
import json

WEB_ROOT = Path("/content/papermorph-studio/web")

def test_nextjs_structure_and_apphosting_config():
    assert (WEB_ROOT / "package.json").exists()
    assert (WEB_ROOT / "tsconfig.json").exists()
    assert (WEB_ROOT / "apphosting.yaml").exists()
    pkg = json.loads((WEB_ROOT / "package.json").read_text())
    assert "next" in pkg["dependencies"]

def test_bilingual_rtl_and_accessibility_attributes():
    reader_code = (WEB_ROOT / "src" / "components" / "InteractiveReader.tsx").read_text()
    layout_code = (WEB_ROOT / "src" / "app" / "layout.tsx").read_text()
    assert 'dir={isRtl ? "rtl" : "ltr"}' in reader_code
    assert "Vazirmatn" in reader_code
    assert "Vazirmatn" in layout_code
    assert '<track kind="captions"' in reader_code
    assert "scormZipUrl" in reader_code
    assert "sourcesMdUrl" in reader_code

def test_human_in_the_loop_approval_and_cost_guard_ui():
    tl_code = (WEB_ROOT / "src" / "components" / "StageTimeline.tsx").read_text()
    assert "awaiting_approval" in tl_code
    assert "Approve Storyboard & Resume Pipeline" in tl_code
    assert "Cost Guard:" in tl_code
