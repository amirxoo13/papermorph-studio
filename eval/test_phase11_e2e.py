from pathlib import Path
from scripts.run_e2e_smoke import run_single_e2e_job

EVAL_DIR = Path("/content/papermorph-studio/eval/golden_set")

def test_bilingual_end_to_end_smoke_pipeline():
    en_txt = (EVAL_DIR / "en_openstax_photosynthesis.txt").read_text(encoding="utf-8")
    fa_txt = (EVAL_DIR / "fa_persian_story.txt").read_text(encoding="utf-8")

    en_res = run_single_e2e_job("en", "OpenStax Photosynthesis Lesson", en_txt, "textbook_lesson")
    assert en_res["finalState"] == "done"
    assert en_res["ffprobe1080p"]["width"] == 1920
    assert en_res["ffprobe1080p"]["height"] == 1080
    assert en_res["ffprobe9x16"]["width"] == 1080
    assert en_res["ffprobe9x16"]["height"] == 1920

    fa_res = run_single_e2e_job("fa", "داستان نور و برگ", fa_txt, "picture_book")
    assert fa_res["finalState"] == "done"
    assert fa_res["ffprobe1080p"]["width"] == 1920
    assert fa_res["ffprobe9x16"]["height"] == 1920
