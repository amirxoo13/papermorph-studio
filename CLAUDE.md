# Papermorph Studio

A Google Cloud platform on top of the Papermorph engine: it turns books and
stories into animated, narrated films. Built for Google competitions.

Read this file fully before doing anything. Everything in it was paid for in
real failures.

---

## 1. The three repositories — never confuse them

| Repo | Role | Write access |
|---|---|---|
| `DozenTwelve/Papermorph` | upstream engine | READ-ONLY, never push |
| `amirxoo13/Papermorph` | our fork | sync ONLY via GitHub's "Sync fork" button |
| `amirxoo13/papermorph-studio` | this repo, the platform | this is where we work |

The engine is vendored at `services/render-job/vendor/papermorph/`.

**Never hand-write, edit, move or delete anything under `vendor/`.** Vendored
code is cloned, never authored. A previous agent wrote fake code there and it
cost two days. To update it, re-clone from the fork and verify with a full-tree
hash manifest (see §6).

## 2. Google Cloud

- Project `gen-lang-client-0484425781`, region `us-central1`, Firestore `nam5`
- Cloud Run Job `pm-render-job`; services `pm-api`, `pm-mcp-tools`, `pm-sandbox`
  (`behi-ai-backend` in the same project belongs to a different project — leave it)
- Buckets `*-pm-raw-uploads`, `*-pm-work`, `*-pm-published`
- Cloud Run Job without GPU: 168 h task timeout. With GPU: 1 h. **So no GPU.**
- Vertex uses ADC. No key file. The runtime SA needs `roles/aiplatform.user`.

## 3. Budget and models

Google model API calls on Vertex are deducted from the **$1000 credit** —
verified in the owner's Cloud Billing console, about $8 drawn over two days.
Billing is the only authority here; never reason from SKU names or pricing pages.

**Use:** `gemini-4-argon` (authoring, competition-compliant), `gemini-3.8-flash`
and the 3.x flash family (mechanical steps), `gemini-3-pro-image` /
`gemini-3.1-flash-image` / `gemini-nano-banana-2.1` (pictures),
`veo-3.1-generate-001` / `veo-3.1-fast-generate-001` (video),
`gemini-3.8-flash-tts` (speech), Lyria 3 (music).

**Retired, never use:** `gemini-2.5-pro` / `-flash` / `-flash-lite`,
`gemini-2.0-flash*`, all `imagen-*` and `*@imagegeneration`, `veo-3.0-*`,
`veo-2.0-*`, `gemini-3-pro-preview`.
(`gemini-2.5-flash-image` is NOT retired — only the 2.5 text models are.)

**Cash only, never plan around:** Claude, Llama, Mistral and every partner MaaS
model.

**The binding constraint is quota, not money.**
- `gemini-3.1-flash-image`: about 2 requests/minute (measured).
- `gemini-4-argon` on the `global` endpoint: hit 429 during a research phase and
  killed a run. Regional endpoints have separate quota pools.

## 4. The engine — read before proposing any architecture

Every statement below was verified by reading the vendored source. Most plans
fail because they were written without doing that.

- **Frames are already piped.** `export.py` runs
  `ffmpeg -f image2pipe -c:v mjpeg` with `Popen(stdin=PIPE)`. No PNG ever
  touches disk. Do not "fix" this.
- **Generated video is never played as video.** `video.py` makes a clip, then
  `frames.py` turns it into an ink-line sprite sheet played on the beat clock,
  "which a `<video>` would not" match for pause, seek and export. Never stitch
  AI clips with `ffmpeg concat` as the film.
- **Word timings are solved, for free.** `tts.py` (Edge or Kokoro) writes
  `timings.js` with the start time of the word after every `[[mark]]`.
  Do not add a paid STT or forced-alignment service.
- **Music is solved.** `music.py` cuts one recording to the film's length so the
  last note lands on the end.
- **Pictures:** `paint.py` → OpenRouter, `paint_openai.py` → OpenAI,
  `paint_vertex.py` (ours, `services/render-job/`) → Vertex. All three share
  `ledger.py`; `paint.py --total LEDGER` sums them.
- **Four tiers:** lesson, picture, documentary, shorts. `new_book.py <tier> <slug>`.
  Shorts are the upright 900×1600 stage; words must stay inside x 50–810,
  y 130–1290.
- **The pipeline:** author `site/<book>/chNN/` → `serve.py 8765 site` →
  `export.py` → `scorm.py`. `export.py` is deterministic because it renders by
  seeking the clock.

### Measured reality

| | film | frames | render | ratio |
|---|---|---|---|---|
| `tulip-mania` (17 pictures) | 200 s | 5999 | 224 s | 1.12× |
| `millions-of-cats` (511 pictures) | 385 s | 11563 | 648 s | 1.66× |

Cloud Run has no hardware H.264 encoder, so `export.py` falls back to libx264.
A light book renders at about 1.1× realtime, a heavy one at about 1.7×.

## 5. Our own files in `services/render-job/`

- `entrypoint.sh` — the authoring pipeline. `TIER` selects the tier; any tier
  other than `picture` **requires** an explicit `BRIEF` or the container exits 15.
- `render_only.sh` — `RENDER_ONLY=1` renders a book already finished inside the
  image, with zero model calls. Prints `RENDER_WALL_SECONDS`.
- `paint_vertex.py` — the Vertex painter. Same CLI as `paint_openai.py`.
  Refuses `--q high`, refuses to overwrite without `--force`, waits out 429 with
  bounded backoff, and **exits non-zero if the returned image has pixel standard
  deviation below 1.0** (a blank image can never report success).
- `stories/` — scenarios. `derby-goal.md` is a 12-shot animated sports short.

## 6. The proof contract

A claim without its proof is a lie. One acceptable proof per claim:

| Claim | The only acceptable proof |
|---|---|
| the model ran | raw `usage_metadata` |
| it cost $X | Cloud Billing, or `paint.py --total LEDGER` |
| the code is the right version | `git rev-parse` + `sha256sum` |
| the vendor matches upstream | full-tree `git hash-object` manifest diff, empty |
| the video exists | `ffprobe` + `ls -l` |
| the service is live | `curl -I` / `gcloud run ... describe` |
| the scene is valid | `lint.py` and `check.py` exit codes, nothing else |

Verifying the vendor:

```bash
git ls-tree -r <upstream-sha> | sed -E 's/^[0-7]+ blob ([0-9a-f]{40})\t/\1\t/' | sort -k2 > want.tsv
find "$VEND" -type f | sort > abs.txt
sed "s|^$VEND/||" abs.txt > rel.txt
git hash-object --no-filters --stdin-paths < abs.txt > hashes.txt   # absolute paths: it resolves from the repo root
paste hashes.txt rel.txt | sort -k2 > have.tsv
diff want.tsv have.tsv        # must be empty
```

## 7. Rules learned the hard way

1. **No simulated, fake or placeholder code, ever.** If you cannot do the real
   thing, say so and stop. A fake pipeline once reported success and was caught
   only by the cost: $0.00044 for a claimed five-minute film.
2. **Never use a CLI flag or API parameter you have not proven exists.**
   `playwright screenshot --stream` does not exist. Run `--help` first.
3. **Never put a secret in a cell, a commit or a chat.** `getpass` into
   `~/.git-credentials` at mode 0600, or Secret Manager.
4. **Never run a blocking cell in Colab.** No `logs tail`, no `--stream`, no
   foreground long job. Use `--async` and `gcloud logging read`.
5. **One task per message.** The Colab agent has a 300-second limit.
6. **Cap review ROUNDS, never wall-clock.** Capping time kills work mid-write.
   Three rounds, then stop.
7. **The only quality gates are the engine's own** `lint.py`, `check.py`,
   `still.py`, `safe.py`. Never invent a gate; a byte-size check and a hand-written
   regex both rejected good work.
8. **Never force-push, `reset --hard`, or delete a branch** without showing the
   command and waiting for approval.
9. **Commit and push after every completed task.** The notebook is temporary; it
   was deleted once and only pushed work survived.

## 8. What produced the one bad output

A 47-second, two-scene film with no pictures. The cause was in our own brief,
not the engine:

```
2 scenes maximum ... ONE review pass only
your entire authoring run MUST finish in under 15 minutes
"sets": "drawn in code, not painted (paint.py must never be reached)"
"budget": 0
"look": one sentence
OPENCODE_MODEL=gemini-3.8-flash
```

All six are fixed. If a run fails, **never** respond by reducing the scene count,
switching to a cheaper model, or disabling the art pass. Those are exactly the
changes that caused it.

## 9. Language

The owner reads Persian. Explain in Persian; keep code, commits, the README and
everything in this repo in English, as the competition requires.
