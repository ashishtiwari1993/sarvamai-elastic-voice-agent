# CLAUDE.md — Bharat Bank · Mitra Voice Agent

Context for Claude Code working in this repo.

## What this is
A demo of a multilingual ("where is my money?") voice bank agent for India:
the caller speaks Hindi/English, the agent verifies identity, reads their
**real transaction history from Elasticsearch**, and answers in their language.

- **Brain:** Elastic Agent Builder agent grounded in Elasticsearch.
- **Voice/language:** Sarvam AI (STT, translate, TTS) — Indian languages.
- **Rule:** Elasticsearch is always queried in English; Sarvam translates both ends.

## Architecture
```
mic → Sarvam STT (saaras:v3) → Sarvam translate→EN (mayura:v1)
    → Elastic Agent Builder /converse (3 tools)
    → Sarvam translate→caller lang → Sarvam TTS (bulbul:v2) → audio
```

### Elasticsearch indices
- `bank-support-kb` — generic knowledge, `content` (text) + `content_semantic`
  (`semantic_text`, inference `.jina-embeddings-v5-text-small`). Hybrid search.
- `bank-transactions` — private per-customer transactions (ES|QL, scoped by `customer_id`).
- `bank-customers` — private profiles incl. `dob` for identity verification.

### Agent Builder (created by scripts/03_create_agent.py)
Agent `bharat-bank-support-agent` with 3 tools:
- `bank_kb_search` (index_search → bank-support-kb)
- `customer_profile` (esql, param `customer_id`) — used to verify DOB
- `customer_transactions` (esql, param `customer_id`) — recent transactions

The agent verifies the caller's date of birth (from `customer_profile`) before
revealing money details. The backend passes the authenticated `customer_id` as
trusted context and keeps a per-caller Agent Builder `conversation_id` so
verification persists within a call.

## Layout
- `data/` — knowledge_base.json (generic), customers.json (profiles + demo callers),
  transactions.json (snapshot; regenerated each ingest).
- `scripts/` — 01_create_index, generate_transactions (dynamic last-30-day dates),
  02_ingest_data, verify_search, 03_create_agent.
- `backend/` — sarvam.py (Sarvam client), elastic_agent.py (converse SSE client),
  app.py (FastAPI: /api/voice, /api/text, /api/customers, /api/reset).
- `frontend/index.html` — single-file Tailwind UI, served by the backend at `/`.

## Commands
```bash
# First-time / full reset (recreates indices, regenerates 100+ txns, recreates agent, serves)
./run_demo.sh

# Day-to-day: just run the server (data already loaded)
./start.sh                       # → http://localhost:8000

# Individual steps
python scripts/01_create_index.py
python scripts/02_ingest_data.py   # generates transactions dynamically (now-30d) + ingests all 3
python scripts/verify_search.py
python scripts/03_create_agent.py
```

## Conventions / gotchas
- All secrets in `.env` (gitignored). Never hardcode keys. See `.env.example`.
- `ELASTIC_API_KEY` / `KIBANA_API_KEY` must be the **encoded** API key (base64 of `id:secret`).
- Transactions are **generated at ingest time** with dates in the last 30 days —
  re-running `02_ingest_data.py` always refreshes the window. Edit
  `scripts/generate_transactions.py` to change volume/scenarios.
- Sarvam endpoints: STT `POST /speech-to-text`, translate `POST /translate`,
  TTS `POST /text-to-speech` (returns base64 WAV in `audios[]`).
- Agent Builder converse is SSE (`/api/agent_builder/converse/async`); final
  answer is the `message_complete` event's `message_content`.
- Demo customers: CUST1001 Rajesh (pending refund), CUST1002 Priya (UPI fraud),
  CUST1003 Anil (delayed pension), CUST1004 Sunita (pending refund).

## Known environment note
Built in Cowork; the cloud endpoints (`*.elastic.cloud`, `api.sarvam.ai`) must
be reachable from wherever the scripts/server run.
