# Architectural & Model Decisions (`gen-lang-client-0484425781`)

## Phase 0 Verified Pinned Models & Region
- **Primary Region**: `us-central1` (Cloud Run, Eventarc, Vertex AI, Workflows, Cloud Tasks)
- **Firestore Location**: `nam5` (multi-region covering `us-central1`)
- **PRO_MODEL**: `gemini-2.5-pro` (verified live on Vertex AI `us-central1`)
- **FLASH_MODEL**: `gemini-2.5-flash` (verified live on Vertex AI `us-central1`)
- **IMAGE_MODEL**: `imagen-3.0-generate-002` (verified live on Vertex AI `us-central1`)
- **TTS_MODEL_EN**: `en-US-Chirp3-HD-Achernar` (Cloud TTS HD voice)
- **TTS_MODEL_FA**: `fa-IR-Standard-A` with automatic `edge-tts` (`fa-IR-DilaraNeural`) fallback in `PAPERMORPH_TTS_BACKEND`
- **STT_MODEL**: `chirp_2` (Cloud Speech-to-Text v2 word-level timing alignment)
- **ENABLE_VEO_CLIPS**: `false` (feature-flagged off; procedural HTML/Canvas/SVG + Imagen 3 used)
- **ENABLE_LYRIA_MUSIC**: `false` (feature-flagged off; synthesized ambient bed / licensed CC0 audio used)
