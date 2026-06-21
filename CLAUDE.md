# CLAUDE.md — Pratham Bank · Mitr Voice Agent

Guidance for Claude (and humans) working in this repo. Read this first.

## What this is
A demo of a multilingual ("where is my money?") voice banking agent for India.
The caller speaks **Hindi / Marathi / English** (can switch mid-call); the agent
greets them, **verifies identity (date of birth)**, reads their **real
transaction history from Elasticsearch**, and answers in the caller's language.

- **Brain:** Elastic Agent Builder agent grounded in Elasticsearch.
- **Voice/language:** Sarvam AI (STT, translate, TTS) — Indian languages.
- **Core rule:** Elasticsearch is always queried in **English**; Sarvam translates both ends.

## Architecture (one voice turn)
```
mic → Sarvam STT (saaras:v3, detects language)
    → Sarvam translate → English (mayura:v1)
    → Elastic Agent Builder POST /api/agent_builder/converse/async  (SSE)
    → Sarvam translate → caller language
    → Sarvam TTS (bulbul) → base64 WAV → browser plays it
```
The backend (`backend/app.py`) orchestrates these 5 calls and serves the frontend.

### Elasticsearch indices
- `bank-support-kb` — GENERIC knowledge. `content` (text) is `copy_to`
  `content_semantic` (`semantic_text`, embeddings via the `INFERENCE_ID`
  endpoint). Hybrid BM25 + semantic search.
- `bank-transactions` — PRIVATE per-customer transactions (ES|QL, scoped by `customer_id`).
- `bank-customers` — PRIVATE profiles incl. `dob` for identity verification.

### Agent Builder (created by `scripts/03_create_agent.py`)
Agent `pratham-bank-support-agent` with 3 tools:
- `bank_kb_search` (index_search → bank-support-kb)
- `customer_profile` (esql, param `customer_id`) — used to verify DOB
- `customer_transactions` (esql, param `customer_id`) — recent transactions

The backend passes the authenticated `customer_id` as trusted context and keeps a
per-caller Agent Builder `conversation_id` so verification persists within a call.

## Layout
- `data/` — `knowledge_base.json` (generic KB), `customers.json` (profiles +
  demo callers, incl. DOB), `transactions.json` (snapshot; **regenerated each ingest**).
- `scripts/` — `00_teardown` (delete indices+agent+tools), `01_create_index`,
  `generate_transactions` (dynamic last-30-day dates), `02_ingest_data`,
  `verify_search`, `03_create_agent`.
- `backend/` — `sarvam.py` (Sarvam client), `elastic_agent.py` (converse SSE
  client), `app.py` (FastAPI: `/api/voice`, `/api/text`, `/api/customers`, `/api/reset`).
- `frontend/index.html` — single-file Tailwind UI, served by the backend at `/`.
- `docs/demo-script.md` — multilingual role-play screenplay for recording.
- `Dockerfile`, `docker-compose.yml` — containerised run + setup/teardown profiles.

## Commands

### Docker (recommended)
```bash
docker compose --profile teardown up --build   # delete everything in Elastic
docker compose --profile setup    up --build   # create indices + ingest + agent
docker compose up --build                        # run → http://localhost:8000
```

### Without Docker
```bash
pip install -r requirements.txt
python scripts/00_teardown.py        # optional: clean slate
python scripts/01_create_index.py
python scripts/02_ingest_data.py     # generates 100+ last-30-day txns + ingests all 3
python scripts/verify_search.py      # optional semantic-search check
python scripts/03_create_agent.py
./start.sh                           # serve only (data already loaded)
./run_demo.sh                        # full reset + serve
```

## Environment (`.env`; see `.env.example`)
- `ELASTICSEARCH_URL`, `ELASTIC_API_KEY` — ES (encoded API key = base64 of `id:secret`).
- `KIBANA_URL`, `KIBANA_API_KEY` — Agent Builder (ES host with `.es.`→`.kb.`).
- `SARVAM_API_KEY` — Sarvam AI.
- `INFERENCE_ID` — **embeddings** endpoint for `semantic_text` (MUST be a
  `text_embedding` endpoint, e.g. `.jina-embeddings-v5-text-small`).
- `AGENT_INFERENCE_ID` — OPTIONAL **chat-completion** endpoint the agent reasons
  with; sent as `inference_id` on `/converse`. Blank = Agent Builder default model.
- `SARVAM_STT_MODEL` (`saaras:v3`), `SARVAM_TRANSLATE_MODEL` (`mayura:v1`).
- `SARVAM_TTS_MODEL` + `SARVAM_TTS_SPEAKER` — **must match** (see gotchas).
- `SARVAM_SPEAKER_GENDER` (`Male`/`Female`) — sets Hindi/Marathi verb gender.

## Conventions / gotchas
- Secrets only in `.env` (gitignored, not baked into the Docker image). Use `.env.example` as the template.
- **Two different "inference ids":** `INFERENCE_ID` = embeddings (semantic_text);
  `AGENT_INFERENCE_ID` = the agent's LLM. Don't cross them — a chat model can't embed.
- Transactions are **generated at ingest time** with dates in the last 30 days
  (`scripts/generate_transactions.py`). Re-running `02_ingest_data.py` refreshes
  the window. The "story hook" txns (disputed UPI debit, pending refund/pension)
  are anchored to recent offsets so demos stay valid.
- **TTS voice/model pairing:** `shubh` and most 30+ voices are **bulbul:v3** only;
  `bulbul:v2` = anushka/manisha/vidya/arya (F), abhilash/karun/hitesh (M). Mismatch → 400.
  `sarvam.py` sends only text/target_language_code/speaker/model (no v2-only params).
- **Speaker gender:** translation (`mayura`) takes `speaker_gender`; set it to match
  the TTS voice or Hindi/Marathi verbs sound the wrong gender ("rahi" vs "raha").
- **Agent prompt/tool changes require re-running `03_create_agent.py`** — they live
  in Kibana, not the backend. Backend/frontend changes are picked up by uvicorn
  `--reload` (frontend just needs a browser refresh; it's static).
- Converse is **SSE** (`/converse/async`); final answer = `message_complete` event's
  `message_content`. `elastic_agent.py` also surfaces `error` events instead of
  silently returning the empty-answer fallback.
- Sarvam endpoints: STT `POST /speech-to-text`, translate `POST /translate`,
  TTS `POST /text-to-speech` (returns base64 WAV in `audios[]`).
- **Mic** needs `http://localhost` or HTTPS; otherwise use the typed-question box.
- Demo customers: CUST1001 Rajesh (pending refund), CUST1002 Priya (UPI fraud),
  CUST1003 Anil (delayed pension), CUST1004 Sunita (pending refund). DOBs are in
  `data/customers.json` (shown in the UI as a presenter hint).

## Common edits
- **Agent persona / rules:** edit `INSTRUCTIONS` in `scripts/03_create_agent.py`, then re-run it.
- **Add KB content:** add objects to `data/knowledge_base.json`, re-run `02_ingest_data.py`.
- **Change voice:** set `SARVAM_TTS_MODEL` + `SARVAM_TTS_SPEAKER` + `SARVAM_SPEAKER_GENDER` in `.env`, restart.
- **Speed up the agent:** point `AGENT_INFERENCE_ID` at a fast endpoint; trim the
  `customer_transactions` `LIMIT`; reduce tool calls in the prompt.

## Known environment note
Cloud endpoints (`*.elastic.cloud`, `api.sarvam.ai`) must be reachable from
wherever the scripts/server run. All data is synthetic; "Pratham Bank" is fictional.
