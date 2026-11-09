# Fake-code audit — open items, not a clean bill of health

This file previously opened with "HISTORICAL RECORD, NOT THE CURRENT SYSTEM"
and "It does NOT describe the current system", while at least eight of the
items it listed were still in the code exactly as written. A reader — human or
agent — would have believed the work was done. That framing was the single most
misleading thing in the repository, so this file now states only what is true
at the commit that touched it, and anything unfixed stays listed.

**Rule for this file: an item is deleted only when the code it names is gone or
real, and the commit that did it is named here.** Never mark an item fixed
because an intention to fix it exists.

---

## Removed

The whole fake surface is deleted, not patched. Commit: see
`git log --follow FAKE_AUDIT.md`.

- `services/mcp-tools/` — deleted. It was a deployed Cloud Run service in which
  almost every tool fabricated its result:
  - `image_generate` drew a beige 1920x1080 rectangle with `PIL.ImageDraw` and
    uploaded it as the scene illustration. No image model was ever called.
  - `contact_sheet_build` uploaded a blank white PNG, so the visual critic
    reviewed an empty image.
  - `stt_word_timings` did `except Exception: pass` and then invented uniform
    word timings by dividing duration by word count, labelled
    `"confidence": 0.99`.
  - `signed_url_create` returned a fabricated `storage.mtls.cloud.google.com`
    URL that cannot work. It never called `generate_signed_url`.
  - `docai_extract` was `text.split("\n\n")`, not Document AI.
  - `vertex_search_index` / `vertex_search_query` stored chunks in Firestore and
    ranked by Python `set.intersection`, not embeddings or Vertex Search.
  - `video_clip_generate` / `music_generate` returned static dicts without
    calling Veo or Lyria.
  - `render_shard_submit` computed shard paths in memory and launched nothing.
  - `tts_synthesize` silently fell back from the requested language to
    `en-US-Neural2-D`, so a Persian film could come out in English.
- `services/agents/papermorph_agents/agent.py` and its 21 `sub_agents/` —
  deleted. `agent.py` swallowed every Vertex failure with a bare
  `except Exception` and substituted `_grounded_extractive_storyboard`, a
  deterministic sentence splitter, so a total model outage still produced a
  "storyboard". It also did
  `t_in = int(getattr(usage, "prompt_token_count", 0) or 120)` and the same with
  `350`, so when the real token counts were missing or zero it fed the literals
  120 and 350 into the cost tracker — a fabricated cost.
- `scripts/run_e2e_smoke.py` — deleted. It synthesized a 4-second Pillow video
  while writing `durationMs=300000` into the book document and into BigQuery.
- `services/api/src/main.py` embedded `STUDIO_HTML` demo UI — already gone
  before this pass.

Kept from `services/agents`, because they are real and useful:
`budget.py` and `duration.py`, moved to `services/common/`.

## Fixed in the code — none of it is deployed

Verified live on 2026-11-09: the running `pm-api` revision is `pm-api-00007-fr4`,
built from `374743f`, so every item in this section is true of `main` and false
of the service the internet can reach. See `reports/LIVE_VERIFICATION.md`.

- **Authentication.** `verify_caller` trusted an `X-Firebase-Uid` header
  verbatim, and for bearer tokens hashed whatever string it was given into a
  uid — so `Authorization: Bearer hello` was a valid, stable identity, and
  `firebase_admin` appeared nowhere in the repo. It now verifies an Identity
  Platform ID token (`services/api/src/auth.py`).
- **Nothing started a job.** `POST /v1/jobs` wrote a `queued` document and
  returned; no Cloud Task, no Workflow, no render job. It now enqueues a Cloud
  Task which calls `/internal/jobs/{id}/start`, which executes
  `pm-render-job` (`services/api/src/dispatch.py`).
- **`GET /v1/books/{id}` had no caller check at all.** It now requires a
  verified caller and allows owner-or-public, matching `firestore.rules`.
- **`/internal/stage-callback` accepted the call and discarded it.** It now
  records the transition.
- **The internal HMAC secret had a hardcoded default**
  (`"papermorph-dev-hmac-secret"`), so the internal endpoint was open if the env
  var was unset. Internal endpoints now verify a Cloud Tasks OIDC token and
  fail closed with 503 when unconfigured.
- **Idempotency and rate limiting were in-process dicts**, useless across Cloud
  Run instances and lost on every cold start. Both now live in Firestore.
- **CORS was `allow_origins=["*"]` with `allow_credentials=True`**, which is not
  a valid configuration. Origins are now explicit, from `PM_ALLOWED_ORIGINS`.
- **The cost table priced every unknown model as a retired cheap Flash model
  and priced unknown media at zero** — the mechanism behind the $0.00044
  "five-minute film" in CLAUDE.md §8. Unknown and not-yet-verified models now
  raise `UnknownModelPricing`.
- **CI built and pushed images but never deployed**, and tagged everything
  `v1.0.0` so no build was identifiable. `cloudbuild.yaml` now tags with
  `$COMMIT_SHA` and deploys.
- **`web/` made no API call at all.** There was not one `fetch`, `useEffect` or
  API call in `web/src`; `app/jobs/[jobId]/page.tsx` hardcoded a
  `placeholderJob` with `costUsd: 0.142` and `app/books/[bookId]/page.tsx`
  hardcoded `/demo/final_1080p.mp4`. Both pages now sign in
  (`web/src/lib/firebase.ts`), fetch the real document
  (`web/src/lib/api.ts`), poll only while the job is still being worked on, and
  show an error rather than a substitute when a request fails.
- **`ContentFormat` had three values for the engine's four tiers**, collapsing
  documentary and shorts into `documentary_shorts`, so an upright 900x1600
  short was unreachable through the API. All four tiers now exist, the legacy
  value still parses, and an unrecognised format raises instead of silently
  defaulting to documentary.

## Still open — nobody has fixed these

1. **The engine was hand-edited inside `vendor/`.** The Persian `fa`
   translations, `RTL_LANGUAGES = ['ar', 'fa']` and the `check_persian_lesson`
   addition to `engine/check_i18n.py` exist only in this repo's vendored copy.
   Neither upstream `DozenTwelve/Papermorph` (`9628d3c`) nor the fork
   `amirxoo13/Papermorph` (`342e272`) has them. This breaks the one check in
   CLAUDE.md §6 that was passing, and the next re-clone of the vendor deletes
   the Persian work. It must be pushed to the fork and tagged, and §6's
   baseline changed from upstream to that tag.
2. **`infra/` defines no Cloud Run service or job.** `infra/cloud_run.tf` is
   image digests and outputs only, so the compute was created by hand and is not
   reproducible from Terraform.
3. **Report commit SHAs cannot be resolved.** Of the ten 40-character SHAs in
   `reports/`, only `9628d3cf` (an upstream Papermorph commit, in phase-0)
   exists in any of the three repositories. The other nine, which are supposed
   to be this repo's own phase commits, are unreachable — probably orphaned by
   the amend-then-"record SHA" pattern in the history. So section 7 of every
   report is unverifiable, against CLAUDE.md §6.
4. **The Cloud Run render proof is partial.** Measured 2026-11-09 with
   `ffprobe` on `gs://...-pm-published/renders/zahhak/ch01/ch01.mp4`, written by
   execution `pm-render-job-q2dnw`: `960x540`, `20/1` fps, `duration=72.051`.
   Real engine output, and the first Persian one, but not a full-length 1080p30
   render. Three of the five `pm-render-job` executions failed. The 1.12x /
   1.66x ratios in CLAUDE.md §4 did not come from any of these runs.
5. **Everything in "Fixed" above is unverified against the live project**, and
   as of 2026-11-09 it is known to be undeployed. `reports/VERIFY.md` lists the
   commands; `reports/LIVE_VERIFICATION.md` holds the first run of them.
6. **The live API accepts any identity, from anyone.** `pm-api` carries
   `allUsers` → `roles/run.invoker`, and the deployed `verify_caller` hashes an
   unverified bearer token into a uid. Proven on 2026-11-09 by a `POST /v1/jobs`
   with `X-Firebase-Uid: attacker-i-am-not-a-user`, which returned `200` and a
   job owned by that string. This is the most urgent item in the repository: it
   closes the moment `pm-api` is redeployed from `main`.
7. **The four fake "books" are still live.** `books/job-*/final_1080p.mp4` in
   the published bucket are 303-307 KB each; `ffprobe` on one reports
   `duration=4.042667` against a Firestore document that says
   `targetDurationMs: 300000`, `state: done`, `costUsd: 0.001168`, all ten
   stages run, and a licence crediting the retired `Imagen 3`. Their producer
   (`scripts/run_e2e_smoke.py`) is deleted on `main`, but the artifacts and
   their Firestore documents are not. They must be deleted, along with
   `jobs/job-836254a42bd5`, the document left by the security probe above.
