# Live verification — 2026-11-09

First verification run executed against the live project from an authenticated
`gcloud` on the owner's own machine (account `kenneth65gray9269@gmail.com`,
Google Cloud SDK 591.0.0). Everything below is raw tool output, not a summary of
intent. Per CLAUDE.md §6, each claim names the one proof that is allowed to
support it.

Nothing here was changed. This run was read-only except for one `POST /v1/jobs`
probe, noted and tracked below.

---

## 1. The infrastructure is real

`gcloud run services list --region=us-central1`

| Service | Last deployed |
|---|---|
| `pm-api` | 2026-11-04T14:04:17Z |
| `pm-mcp-tools` | 2026-11-04T11:55:27Z |
| `pm-sandbox` | 2026-11-04T11:54:54Z |
| `behi-ai-backend` | 2026-11-03 — a different project, left alone (CLAUDE.md §2) |

`gcloud run jobs list` → `pm-render-job`, created 2026-11-04, last run
2026-11-09 17:23:42 UTC.

`gcloud storage buckets list` → `*-pm-raw-uploads`, `*-pm-work`,
`*-pm-published` all exist.

`gcloud artifacts repositories list --location=us-central1` → repository
`papermorph`, 20562.563 MB, updated 2026-11-09T19:39:07.

## 2. The deployed API has no authentication — proven

`gcloud run services get-iam-policy pm-api` shows `allUsers` holds
`roles/run.invoker`, so the service is reachable by anyone on the internet. The
401 that an unauthenticated request receives therefore comes from the
application, not from Google's front end.

The deployed revision is `pm-api-00007-fr4`, image
`...papermorph/pm-api@sha256:bbfdfddc...`. Its `verify_caller` is the one in
commit `374743f`, not the one on `main`:

```python
uid = x_firebase_uid
if not uid and authorization and authorization.startswith("Bearer "):
    token = authorization.split(" ", 1)[1].strip()
    if token:
        uid = f"uid-{hashlib.sha256(token.encode()).hexdigest()[:12]}"
```

A header value is taken as an identity, and a bearer token is **hashed, never
verified**. Three `curl` calls against the live URL:

| Request | Result |
|---|---|
| no credentials | `401 {"detail":"Missing authentication credentials"}` |
| `X-Firebase-Uid: attacker-i-am-not-a-user` | `404 {"detail":"Job not found"}` — accepted |
| `Authorization: Bearer this-is-not-a-real-token-at-all` | `404 {"detail":"Job not found"}` — accepted |

And a write succeeded:

```
POST /v1/jobs   X-Firebase-Uid: attacker-i-am-not-a-user
200 {"job":{"jobId":"job-836254a42bd5","ownerUid":"attacker-i-am-not-a-user",...,"state":"queued"}}
```

**Any person on the internet can create jobs under any identity on the live
service.** The fix (`services/api/src/auth.py`, real `verify_id_token`) is on
`main` at `87a6827` and is **not deployed**.

Cleanup owed: Firestore document `jobs/job-836254a42bd5` was created by that
probe and still exists. It must be deleted.

## 3. The API's "finished films" are 4-second placeholders — proven

`gcloud storage ls -l` on the published bucket separates two populations.

Written by the engine (`render_only.sh` / `export.py`):

```
 246553395  renders/millions-of-cats/ch01/ch01.mp4
  55332430  renders/tulip-mania/ch01/ch01.mp4
  11836021  renders/zahhak/ch01/ch01.mp4      (2026-11-09T17:26:19Z)
 244462596  examples/millions-of-cats/ch01.mp4
 112312188  examples/three-little-pigs/ch01.mp4
  64150131  examples/joke-collection/ch01.mp4
```

Written by the API path:

```
    303069  books/job-09d385c2335d/final_1080p.mp4
    305806  books/job-74f7982c1c7f/final_1080p.mp4
    306983  books/job-8e7e98cb5067/final_1080p.mp4
    303069  books/job-a65e6b632932/final_1080p.mp4
```

All four within two minutes of each other on 2026-11-04, and two of them share
a byte-identical size. `ffprobe` on the first:

```
codec_name=h264  width=1920  height=1080  r_frame_rate=24/1
duration=4.042667   size=303069   bit_rate=599740
```

**4.04 seconds.** Its Firestore document claims otherwise:

| Field | Value |
|---|---|
| `title` | داستان نور و برگ |
| `ownerUid` | `e2e-smoke-tester` |
| `state` | `done` |
| `targetDurationMs` | `300000` (5 minutes) |
| `actualDurationMs` | `null` |
| `costUsd` | `0.001168` |
| `stageAttempts` | all ten stages recorded as run |
| `artifacts` | `{}` — empty |
| `createTime` → `updateTime` | 10:37:37 → 10:37:47 — **ten seconds** |
| `licences` | claims `Proprietary-Vertex-Imagen3` and `Proprietary-Google-Cloud-TTS` |

This is CLAUDE.md §7.1 happening again, live: a pipeline that reports success
for a five-minute film it never made, caught by the cost — $0.001168 here,
against the $0.00044 that was caught the first time. It also credits
`Imagen 3`, which CLAUDE.md §3 lists as retired and never to be used.

The producer was `scripts/run_e2e_smoke.py` (the `e2e-smoke-tester` uid), which
is deleted on `main` at `87a6827`. The four artifacts and their Firestore
documents are still in the live project and must be removed.

## 4. The one real Cloud Run render is still a partial proof

`ffprobe` on `renders/zahhak/ch01/ch01.mp4`, written 2026-11-09T17:26:19Z:

```
codec_name=h264  width=960  height=540  r_frame_rate=20/1
duration=72.050998   size=11836021   bit_rate=1314182
```

72 seconds at 540p/20fps. Real output from the real engine, and the first
Persian one, but not the 1080p30 full-length render that FAKE_AUDIT item 4 is
waiting on. Of the five `pm-render-job` executions, two succeeded
(2026-11-09 17:23, 2026-11-05 17:28) and three failed.

---

## 5. The hole is closed — deployed and re-probed

`pm-api` was redeployed the same evening. Cloud Build
`f3a5094c-e19a-4ee4-a778-fa22ecf401ec` cloned the public repo, **refused to
continue unless `git rev-parse HEAD` equalled
`618c7913bad7239a1a2d775876f197ca3384c0b1`**, ran the 13 unit tests, built from
`services/api/Dockerfile`, and deployed. `gcloud run services describe pm-api`:

```
pm-api-00008-jkd   .../papermorph/pm-api:618c7913bad7239a1a2d775876f197ca3384c0b1
```

The same probes from section 2, re-run against the same URL:

| Request | Before | After |
|---|---|---|
| no credentials | `401` | `401 Missing bearer token: send 'Authorization: Bearer <Identity Platform ID token>'` |
| `X-Firebase-Uid: attacker-i-am-not-a-user` | `404` — accepted | `401` — header no longer carries identity |
| `Authorization: Bearer this-is-not-a-real-token-at-all` | `404` — accepted | `401 Invalid ID token: InvalidIdTokenError` |
| `POST /v1/jobs` with a made-up uid | `200`, job created | `401` |
| `POST /internal/jobs/whatever/start` | — | `403 Missing internal OIDC token` |
| same, with a junk bearer | — | `403 Invalid internal OIDC token: MalformedError` |
| `POST /internal/stage-callback` | accepted and discarded | `403 Missing internal OIDC token` |

`InvalidIdTokenError` is `firebase_admin` rejecting a signature, so the token is
being verified and not hashed.

Cloud Run IAM still carries `allUsers` → `roles/run.invoker`, deliberately: a
browser cannot mint a Google-signed OIDC token for a Cloud Run service, so
closing that layer would lock the web app out of its own API. The gate is
`verify_caller`, and `/internal/*` has its own, as the table shows.

### Three bugs this deploy found, none of which reading the code would have

1. `PM_TASKS_QUEUE` defaulted to `pm-job-queue`. The queue in the project is
   `papermorph-job-queue`, so every enqueue would have failed.
2. `cloudbuild.yaml` deployed with `--no-allow-unauthenticated`, which would
   have made the API unreachable from any browser.
3. Both build files passed `--set-env-vars "^:^..."`, and `:` splits
   `https://` in half. Build `9d8f7a14-63c3-4a6e-aca3-4b8ac76b9d44` failed with
   `Bad syntax for dict arg: [//pm-api-149479920662.us-central1.run.app]`. The
   delimiter is now `##`.

Fixed in `8212202` and `618c791`.

---

## What this run did not verify

Authentication, CORS and the internal endpoints are now proven live (section 5).
Nothing else is. No job has been created with a real Identity Platform token, so
the Cloud Tasks enqueue, `/internal/jobs/{id}/start`, the `pm-render-job`
execution it triggers, `UnknownModelPricing` and the web app have never run
against this project. That is one end-to-end job away, and it needs a signed-in
user; `reports/VERIFY.md` holds the commands.

The two cleanups this run identified are also still owed, and were deliberately
not done: the four 4-second `books/` artifacts with their Firestore documents,
and `jobs/job-836254a42bd5`, the document the security probe left behind.
