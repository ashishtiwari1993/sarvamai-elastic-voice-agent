# 🛡️ Pratham Bank · Mitr — Multilingual Voice Banking Agent

> A reference implementation of a **voice AI agent for Indian banking**, built with
> **Elastic Agent Builder** (the brain, grounded in Elasticsearch) and **Sarvam AI**
> (speech‑to‑text, translation, text‑to‑speech for Indian languages).

A customer calls in and speaks naturally — in **Hindi, Marathi, or English**, even
switching language mid‑call. The agent **greets them**, **verifies their identity**,
looks up their **real transaction history in Elasticsearch**, and answers — in the
caller's own language — *"where is my money?"*: a pending refund, a delayed pension,
a salary credit, or a **suspicious UPI debit** that needs to be reported as fraud.

```
🎙️ Caller speaks (hi / mr / en)
        │
        ▼
  Sarvam STT  ──►  Sarvam Translate → English  ──►  Elastic Agent Builder
 (saaras:v3)         (mayura:v1)                    (verifies ID, queries the
        ▲                                            caller's transactions + KB)
        │                                                     │
  Audio played ◄── Sarvam TTS ◄── Sarvam Translate ◄──────────┘
  (bulbul)              (back to caller's language: the English answer)
```

> **Design rule:** Elasticsearch is always queried in **English**; the caller is
> always heard and answered in **their own language**. Sarvam translates both ends.

---

## 🎥 Demo

<!--
  EMBED YOUR VIDEO HERE. Pick ONE of the two options below:

  Option A — GitHub-hosted (recommended for .mp4/.mov):
    1. Open this repo on github.com → create a new Issue (don't submit it) OR
       edit the README via the web editor.
    2. DRAG-AND-DROP your video file into the text box. GitHub uploads it and
       inserts a link like https://github.com/user-attachments/assets/XXXX.
    3. Paste that exact URL on its own line below — GitHub renders a player.

  Option B — YouTube (GitHub can't embed iframes, so use a clickable thumbnail):
    [![Watch the demo](https://img.youtube.com/vi/VIDEO_ID/maxresdefault.jpg)](https://youtu.be/VIDEO_ID)
-->

https://github.com/USERNAME/REPO/raw/main/assets/sarvamai-elastic-voice-agent.mp4

▶️ Fallback: **[watch the demo video](assets/sarvamai-elastic-voice-agent.mp4)**

> The bare `raw` URL above renders an **inline player** on github.com. Replace
> `USERNAME/REPO` with your repo path (and `main` if your default branch differs).
> The video is committed at `assets/sarvamai-elastic-voice-agent.mp4`. If you'd
> rather not commit a large file, drag it into a GitHub issue to get a hosted
> `…/assets/…` URL and paste that here instead.

## ✨ What this demonstrates

- A **voice agent** built on Elastic Agent Builder with **zero custom RAG plumbing** —
  the agent orchestrates tools and the LLM inside Elastic.
- **Private, per‑customer data** (transactions, profiles) queried safely with
  **parameterised ES|QL tools** scoped to one `customer_id`.
- **Semantic search** over a knowledge base using `semantic_text` + an inference
  endpoint (no manual embedding pipeline).
- **Identity verification** (date of birth) before any money detail is shared.
- **On‑the‑fly language switching** and natural Indian‑language speech via Sarvam.
- Pluggable **chat‑completion model** for the agent (e.g. point it at a fast Groq
  endpoint) and a configurable TTS **voice**.

---

## 🧠 Architecture

| Layer | Technology | Default |
|------|------------|---------|
| Speech → Text | Sarvam | `saaras:v3` (auto language detect) |
| Translation | Sarvam | `mayura:v1` |
| Reasoning / tools | Elastic Agent Builder | custom agent + 3 tools |
| Agent LLM | Elastic inference / connector | default, or `AGENT_INFERENCE_ID` |
| Embeddings | Elasticsearch inference | `.jina-embeddings-v5-text-small` |
| Text → Speech | Sarvam | `bulbul` |
| Backend | FastAPI (Python) | serves API **and** the frontend |
| Frontend | single‑file HTML + Tailwind | mic UI + typed fallback |

### Elasticsearch indices

| Index | Type | Contents |
|-------|------|----------|
| `bank-support-kb` | generic | Loan/FD rates, fees, UPI‑fraud procedures (1930, cybercrime.gov.in), refund/pension/failed‑txn explainers. Stored as **plaintext + `semantic_text`**. |
| `bank-transactions` | private | **100+ transactions generated at ingest time with dates in the last 30 days** — salary, EMI, UPI, ATM, POS, refunds, pension, with status + running balance. |
| `bank-customers` | private | One profile per customer incl. **date of birth** (for verification), KYC/UPI/account status. |

### Agent Builder tools

- `bank_kb_search` — `index_search` over `bank-support-kb` (hybrid BM25 + semantic)
- `customer_profile` — ES|QL, returns one customer's profile (used to verify DOB)
- `customer_transactions` — ES|QL, returns one customer's recent transactions

The backend passes the authenticated `customer_id` as trusted context and keeps a
per‑caller Agent Builder `conversation_id`, so verification persists within a call.

---

## ✅ Prerequisites

1. **An Elastic deployment with Agent Builder enabled** (Elastic Cloud / Serverless),
   plus:
   - a **text‑embedding inference endpoint** for `semantic_text`
     (this demo uses `.jina-embeddings-v5-text-small`), and
   - an LLM connector/inference for the agent (the default, or your own
     `chat_completion` endpoint).
2. **A Sarvam AI API key** — <https://dashboard.sarvam.ai>.
3. **Encoded Elastic API key(s)** (base64 of `id:api_key`) with privileges for
   Elasticsearch + Kibana/Agent Builder.
4. Either **Docker** (recommended) **or** Python 3.10+.

---

## 🚀 Quick start (Docker — recommended)

```bash
# 1. Clone and enter
git clone <your-repo-url> pratham-mitr && cd pratham-mitr

# 2. Configure credentials
cp .env.example .env        # then edit .env with your real keys/URLs

# 3. One-time setup: create indices, ingest data (+ embeddings), create the agent
docker compose --profile setup up --build

# 4. Run the voice agent
docker compose up --build   # → open http://localhost:8000
```

Stop with `Ctrl+C` (or `docker compose down`). Re‑run step 3 any time you want to
refresh the data (it regenerates the last‑30‑day transaction window).

## ♻️ Reset / rebuild from scratch

Wipe everything this demo created in Elastic and rebuild cleanly — all via Docker:

```bash
# 1. DELETE all 3 indices + the agent + the 3 tools (incl. any legacy agent)
docker compose --profile teardown up --build

# 2. RE-CREATE indices + ingest data (+ embeddings) + create the agent
docker compose --profile setup up --build

# 3. RUN the app
docker compose up --build         # → http://localhost:8000
```

`teardown` runs `scripts/00_teardown.py`; it only removes this demo's objects and
**does not** touch your inference endpoints (Jina embeddings / Groq). Verify a
clean slate with:

```bash
source .env
curl -s -H "Authorization: ApiKey $ELASTIC_API_KEY" "$ELASTICSEARCH_URL/_cat/indices/bank-*?v"
```

> If answers come back empty after a rebuild, temporarily set `AGENT_INFERENCE_ID=`
> (blank) in `.env` and re-run setup to confirm the agent works with the default
> model — that isolates whether the issue is the custom (Groq) endpoint.

## 🐍 Quick start (without Docker)

```bash
cp .env.example .env        # edit with your keys
pip install -r requirements.txt

python scripts/01_create_index.py     # create the 3 indices (incl. semantic_text)
python scripts/02_ingest_data.py      # ingest KB + customers + generate/ingest txns
python scripts/verify_search.py       # (optional) prove semantic search works
python scripts/03_create_agent.py     # create the Agent Builder tools + agent

./start.sh                            # or: cd backend && uvicorn app:app --port 8000
```

Open **http://localhost:8000**, pick a caller, tap the mic, and ask in Hindi/Marathi/English.

> **Mic note:** browsers only allow microphone access on `http://localhost` or HTTPS.
> If the mic is blocked, use the typed‑question box (same pipeline, minus STT).

---

## ⚙️ Configuration (`.env`)

| Variable | Required | Description |
|----------|----------|-------------|
| `ELASTICSEARCH_URL` | ✅ | ES endpoint (e.g. `https://…es….elastic.cloud:443`) |
| `ELASTIC_API_KEY` | ✅ | **Encoded** ES API key |
| `KIBANA_URL` | ✅ | Kibana endpoint (usually ES host with `.es.`→`.kb.`) |
| `KIBANA_API_KEY` | ✅ | **Encoded** key with Agent Builder privileges |
| `SARVAM_API_KEY` | ✅ | Sarvam AI subscription key |
| `INFERENCE_ID` | ✅ | **text‑embedding** endpoint for `semantic_text` |
| `AGENT_INFERENCE_ID` | – | chat‑completion endpoint for the agent (blank = default) |
| `AGENT_ID` | – | Agent id (default `pratham-bank-support-agent`) |
| `ES_INDEX` / `TXN_INDEX` / `CUST_INDEX` | – | Index names |
| `SARVAM_STT_MODEL` | – | `saaras:v3` |
| `SARVAM_TRANSLATE_MODEL` | – | `mayura:v1` |
| `SARVAM_TTS_MODEL` | – | `bulbul:v2` or `bulbul:v3` |
| `SARVAM_TTS_SPEAKER` | – | Voice — **must match the TTS model** |
| `SARVAM_SPEAKER_GENDER` | – | `Male`/`Female` — aligns Hindi/Marathi verb gender to the voice |

> **Voice/model pairing:** `shubh` (and most 30+ voices) are **bulbul:v3** only.
> `bulbul:v2` supports anushka/manisha/vidya/arya (female) and abhilash/karun/hitesh
> (male). A mismatch returns `400` from Sarvam. Set `SARVAM_SPEAKER_GENDER` to match
> the voice so the assistant says "raha hoon" (male) vs "rahi hoon" (female).

---

## 👥 Demo callers & script

Four "logged‑in" callers, each a *"where is my money?"* story:

| Caller | DOB (for verification) | Scenario |
|--------|------------------------|----------|
| Rajesh Kumar (Bengaluru) | 14 Mar 1988 | salary credited, EMI debited, Flipkart refund pending |
| Priya Sharma (Pune) | 2 Nov 1995 | **disputed ₹14,999 UPI debit** → fraud flow |
| Anil Verma (Lucknow) | 21 Jul 1958 | pension delayed / still processing |
| Sunita Devi (Patna) | 9 Jan 1991 | ₹2,499 Meesho refund pending |

A ready‑to‑record, multilingual **role‑play script** (English ↔ Hindi ↔ Marathi) is in
[`docs/demo-script.md`](docs/demo-script.md). The UI shows the DOB as a presenter hint.

---

## 📁 Project structure

```
.
├── data/
│   ├── knowledge_base.json       # generic KB (semantic_text)
│   ├── customers.json            # private profiles (+ DOB) & demo callers
│   └── transactions.json         # snapshot of the last generated txns (auto‑refreshed)
├── scripts/
│   ├── 00_teardown.py            # delete all indices + agent + tools (clean wipe)
│   ├── 01_create_index.py        # create 3 indices (incl. semantic_text mapping)
│   ├── generate_transactions.py  # 100+ txns with dynamic last‑30‑day dates
│   ├── 02_ingest_data.py         # ingest all three (generates txns)
│   ├── verify_search.py          # semantic search sanity check
│   └── 03_create_agent.py        # create Agent Builder tools + agent
├── backend/
│   ├── sarvam.py                 # Sarvam STT / Translate / TTS client
│   ├── elastic_agent.py          # Agent Builder /converse (SSE) client
│   └── app.py                    # FastAPI: /api/voice, /api/text, /api/customers, /api/reset
├── frontend/index.html           # Tailwind UI: caller switcher, mic, audio
├── docs/demo-script.md           # multilingual demo screenplay
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── run_demo.sh                   # full reset + serve (non‑Docker)
├── start.sh                      # serve only (non‑Docker)
├── .env.example
└── LICENSE
```

---

## 🧪 How a turn works

1. **STT** — Sarvam transcribes the audio and detects the language.
2. **Translate → English** — the caller's words become an English query.
3. **Agent** — the backend calls Agent Builder `/converse/async` with the English
   query + authenticated caller context; the agent verifies DOB (first turn), then
   calls `customer_transactions` / `customer_profile` / `bank_kb_search` and returns
   an English answer.
4. **Translate → caller language** — the answer is translated back.
5. **TTS** — Sarvam speaks it; the browser plays the audio.

Each `/api/voice` and `/api/text` response includes a `timings` block (per‑step
seconds) and is logged to the server console as `⏱ /api/voice stt=… agent=… tts=…`.

---

## 🩺 Troubleshooting

| Symptom | Likely cause / fix |
|--------|--------------------|
| `401 security_exception … unable to find apikey` | Wrong/expired API key. Use the **encoded** key; verify with `GET /_security/_authenticate`. |
| `400 … /text-to-speech` | TTS **voice/model mismatch** (e.g. `shubh` needs `bulbul:v3`). |
| Assistant uses wrong gender ("rahi" vs "raha") | Set `SARVAM_SPEAKER_GENDER` to match the voice. |
| `502 Pipeline error: …` | The error names the failing step (STT/translate/agent/TTS). Check the message. |
| High latency | The `agent` step dominates; point `AGENT_INFERENCE_ID` at a fast model and reduce tool calls. |
| Mic does nothing | Use `http://localhost` (not a LAN IP) or HTTPS; or use the typed box. |
| Setup `Address already in use` | A server is already on `:8000` — `docker compose down` or `lsof -ti :8000 \| xargs kill`. |

---

## 🔒 Security & limitations (demo‑grade)

- All data is **synthetic**; "Pratham Bank" and its phone numbers are fictional.
- Caller scoping is enforced by passing a trusted `customer_id` to the agent. **In
  production**, additionally enforce Elasticsearch **document‑level security / RBAC**
  per user, real authentication, and a real telephony/WebRTC layer.
- Secrets live only in `.env` (gitignored / not baked into the Docker image).
- Helpline references (1930, cybercrime.gov.in, RBI Ombudsman) are real Indian
  resources included for realism.

## 📄 License

MIT — see [`LICENSE`](LICENSE).

---

*Built with Elastic Agent Builder + Sarvam AI. Not affiliated with any real bank.*
