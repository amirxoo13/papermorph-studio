# What must be run to prove this commit

The code in this commit was written **without Google Cloud credentials**. What
is proven and what is not:

**Proven here.** `services/api/tests/test_api_units.py` — 13 tests, run with
`PYTHONPATH=. python3 -m pytest -q services/api/tests/test_api_units.py`,
`13 passed`. They need no credentials. Every own-code Python file compiles
(`python3 -m py_compile`). `cloudbuild.yaml` parses as YAML. The web app
typechecks (`npx tsc --noEmit`, exit 0) and builds
(`npm run build`, exit 0, 4 routes).

**Not proven.** Everything that touches the live project: token verification,
the Cloud Task, the job execution, the deploy. No `gcloud` call was made from
the session that wrote this code. Treat every item below as unverified until
its command has been run and its output pasted into a report.

Per CLAUDE.md §7.5, run one task per message in Colab, and never a blocking
cell: use `--async` and `gcloud logging read`.

---

## 1. Deploy this commit

```bash
gcloud builds submit --config cloudbuild.yaml \
  --substitutions \
_SERVICE_BASE_URL=https://pm-api-<hash>-uc.a.run.app,\
_TASKS_INVOKER_SA=pm-orchestrator-sa@gen-lang-client-0484425781.iam.gserviceaccount.com,\
_ALLOWED_ORIGINS=https://<your-hosting-domain> \
  --project gen-lang-client-0484425781 --async
```

The build fails on purpose if any of the three substitutions is empty: without
them `/internal/*` fails closed and nothing can start a job.

Pass when: the build finishes, and

```bash
gcloud run services describe pm-api --region us-central1 \
  --format='value(spec.template.spec.containers[0].image)'
```

prints `pm-api:<this commit SHA>`.

## 2. Authentication is real

This is the one that matters most — the old code accepted any string.

```bash
API=https://pm-api-<hash>-uc.a.run.app

# a) no token  -> expect 401
curl -i -s -X POST "$API/v1/jobs" -H 'Content-Type: application/json' -d '{}' | head -1

# b) a junk bearer token -> expect 401 (this returned 200 before)
curl -i -s -X POST "$API/v1/jobs" \
  -H 'Authorization: Bearer hello' \
  -H 'Content-Type: application/json' -d '{}' | head -1

# c) a forged uid header -> expect 401 (this WAS the identity before)
curl -i -s "$API/v1/jobs/job-anything" -H 'X-Firebase-Uid: someone-else' | head -1
```

Then two **real** users. Create them in Identity Platform, sign each in to get
an ID token, and check that user B cannot read user A's job:

```bash
# user A creates a job, user B asks for it -> expect 403
curl -i -s "$API/v1/jobs/$JOB_ID" -H "Authorization: Bearer $TOKEN_B" | head -1
```

Pass when: (a) (b) (c) are all `401`, and the cross-user read is `403`.
Paste all four status lines.

## 3. A submitted job actually starts a render

```bash
curl -s -X POST "$API/v1/jobs" \
  -H "Authorization: Bearer $TOKEN_A" \
  -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: verify-001' \
  -d '{"title":"Zahhak","format":"documentary","language":"fa",
       "sourceUri":"gs://gen-lang-client-0484425781-pm-raw-uploads/zahhak.txt",
       "brief":"<the real brief>","targetDurationMs":600000,"costCapUsd":7.5}'
```

Pass when all four hold:

1. The response carries a `taskName`.
2. `gcloud tasks list --queue pm-job-queue --location us-central1` shows that task.
3. Within a minute the job document has an `executionName`, and
   `gcloud run jobs executions describe <that name> --region us-central1`
   returns a real execution.
4. Repeating the same call with the same `Idempotency-Key` returns the **same**
   `jobId` and does **not** create a second task. Run it twice and paste both
   responses.

If `POST /v1/jobs` returns `503 Dispatch not configured`, the three
substitutions in step 1 were not set — that is the intended failure, not a bug.

## 4. Rate limiting holds across instances

```bash
for i in $(seq 1 70); do
  curl -s -o /dev/null -w '%{http_code} ' "$API/v1/jobs/none" \
    -H "Authorization: Bearer $TOKEN_A"
done; echo
```

Pass when: the first 60 are `404` (authenticated, job absent) and the rest are
`429`. The count now lives in Firestore, so check
`gcloud firestore documents list --collection-ids=rateLimits` shows the counter.

## 5. The cost table refuses to guess

```bash
PYTHONPATH=. python3 -c "
from services.common.budget import compute_llm_cost, UnknownModelPricing
try:
    compute_llm_cost('gemini-4-argon', 1000, 1000)
    print('FAIL: priced an unverified model')
except UnknownModelPricing as e:
    print('PASS:', e)
"
```

Then read the real Argon and Nano Banana figures from Cloud Billing and add
them to `MODEL_PRICING_USD` with the Billing screen as the source. Until then
any stage using those models must record `tokens_in=0, tokens_out=0` and the
cost must be tracked from Billing only.

## 6. The still-open items

`FAKE_AUDIT.md` lists five. The urgent one needs no cloud:

**The engine fork (item 1).** The Persian `fa` block, `RTL_LANGUAGES` and the
`check_persian_lesson` addition live only in this repo's `vendor/` copy.
Neither upstream (`9628d3c`) nor the fork (`342e272`) has them, so the next
vendor re-clone deletes the Persian work, and CLAUDE.md §6's empty-manifest
check cannot pass. Push them to `amirxoo13/Papermorph`, tag it, re-vendor from
the tag, point `style.json` at it, and change §6's baseline from upstream to
that tag.

## 7. The web app

```bash
cd web && npm ci && npm run build        # expect exit 0
```

Then, with `NEXT_PUBLIC_API_BASE_URL`, `NEXT_PUBLIC_FIREBASE_API_KEY` and
`NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN` set in `apphosting.yaml`, deploy and check
in a browser:

1. Signed out, `/jobs/<id>` says "Sign in to see this job" — it does not render
   a job.
2. Signed in as the owner, the page shows the job's **real** `costUsd`. If you
   ever see `0.142` again, a placeholder has come back.
3. Signed in as another account, the page says the job belongs to another
   account (the API returned 403).
4. While the job is in a working state the page polls every 5 s and stops
   polling once it reaches `done` or `failed`. Watch the network tab.
