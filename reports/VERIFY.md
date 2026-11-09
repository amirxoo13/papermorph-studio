# What must be run to prove this commit

The code in this commit was written **without Google Cloud credentials**. What
is proven and what is not:

**Proven here.** `services/api/tests/test_api_units.py` — 10 tests, run with
`PYTHONPATH=. python3 -m pytest -q services/api/tests/test_api_units.py`,
`10 passed`. They need no credentials. Every own-code Python file compiles
(`python3 -m py_compile`). `cloudbuild.yaml` parses as YAML.

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

`FAKE_AUDIT.md` lists six. Two need no cloud and are the next work:

- the engine fork (item 2) — urgent: the next vendor re-clone deletes the
  Persian work.
- the frontend (item 1) — it still shows `costUsd: 0.142` from a hardcoded
  object.

Neither is touched by this commit.
