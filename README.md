# 🛡️ Bharat Bank · Mitra — "Where Is My Money?" Voice Agent (Elastic Agent Builder + Sarvam AI)

A working demo of a **multilingual voice bank agent** for India. A customer
calls in (in **Hindi or English**, switching freely), the agent **verifies
their identity**, looks up their **actual transaction history in Elasticsearch**,
and tells them — in their own language — *where their money is*: a pending
refund, a delayed pension, a salary credit, or a **suspicious UPI debit** that
needs to be reported as fraud.

- **Brain:** an **Elastic Agent Builder** agent grounded in Elasticsearch data.
- **Voice + language:** **Sarvam AI** (speech-to-text, translation, text-to-speech) — built for Indian languages.

> Design choice: **Elasticsearch is always queried in English**, while the
> customer is heard and answered in their own language. Sarvam translates both ends.

---

## How it works

```
🎙️  Customer speaks (Hindi / English)
      │
      ▼
1) Sarvam  Speech-to-Text   →  transcript + auto-detected language
2) Sarvam  Translate         →  English query
3) Elastic Agent Builder     →  verifies identity (DOB) on the first turn, then:
      │                          • customer_transactions (ES|QL, this caller only)
      │                          • customer_profile      (ES|QL, identity/status)
      │                          • bank_kb_search         (semantic KB: rates, fraud, timelines)
      ▼
4) Sarvam  Translate         →  answer back in the customer's language
5) Sarvam  Text-to-Speech    →  spoken reply  🔊
```

| Layer | Technology | Model |
|------|-------------|-------|
| Speech → Text | Sarvam | `saaras:v3` (auto language detect) |
| Translation | Sarvam | `mayura:v1` |
| Reasoning / tools | Elastic Agent Builder | custom agent + 3 tools |
| Embeddings | Elasticsearch inference | `.jina-embeddings-v5-text-small` |
| Text → Speech | Sarvam | `bulbul:v2` |

---

## Data — three indices

| Index | Type | What's in it |
|-------|------|--------------|
| `bank-customers` | **private** | One profile per customer: name, account, registered mobile (last 4), **date of birth** (for verification), KYC/UPI/account status, products. |
| `bank-transactions` | **private** | **100+ per-customer transactions, generated at ingest time with dates in the last 30 days** (salary, EMI, UPI, ATM, POS, refunds, pension, interest) with amount, channel, counterparty, status (`SUCCESS`/`PENDING`/`FAILED`/`DISPUTED`) and running balance. |
| `bank-support-kb` | **generic** | Loan & FD rates, fees/charges, UPI-fraud procedures (1930, cybercrime.gov.in), and "where is my money" explainers (failed-transaction auto-reversal, refund & pension timelines). Stored as **plaintext + `semantic_text`** (Jina embeddings). |

The private indices are queried with **parameterised ES|QL tools scoped to one
`customer_id`**; the generic index is searched semantically.

### Four demo callers (each a "where is my money" story)
- **Rajesh Kumar** (Bengaluru) — salary credited, home-loan EMI debited, Flipkart refund **pending**.
- **Priya Sharma** (Pune) — a **disputed ₹14,999 UPI debit** to an unknown payee → fraud flow.
- **Anil Verma** (Lucknow) — pensioner whose pension is **still processing** this month.
- **Sunita Devi** (Patna) — waiting on a **₹2,499 Meesho refund**.

---

## Identity verification

Before sharing any balance or transaction, the agent calls `customer_profile`
and asks the caller for their **date of birth**, matching it against the
`bank-customers` index. The demo UI shows the DOB as a small presenter hint so
you know what to say on stage. Verification persists for the rest of the call
(the backend keeps the Agent Builder `conversation_id` per caller).

> Demo-grade scoping: the authenticated `customer_id` is passed to the agent as
> trusted context and every tool is locked to it. In production you would
> additionally enforce Elasticsearch document-level security / RBAC per user.

---

## Setup

### Prerequisites
- Python 3.10+
- An Elastic deployment with **Agent Builder** enabled and the
  `.jina-embeddings-v5-text-small` inference endpoint ready
- A **Sarvam AI** API key (https://dashboard.sarvam.ai)

### 1. Credentials
```bash
cp .env.example .env   # then fill ELASTICSEARCH_URL, ELASTIC_API_KEY,
                       # KIBANA_URL, KIBANA_API_KEY, SARVAM_API_KEY
```

### 2. Run everything
```bash
./run_demo.sh
```
Installs deps → creates the 3 indices → ingests data (+ embeddings) → creates
the agent + 3 tools → serves the UI at **http://localhost:8000**.

### …or step by step
```bash
pip install -r requirements.txt
python scripts/01_create_index.py     # 3 indices (incl. semantic_text)
python scripts/02_ingest_data.py      # KB + transactions + customers
python scripts/verify_search.py       # (optional) prove semantic search works
python scripts/03_create_agent.py     # Agent Builder: 3 tools + agent
cd backend && uvicorn app:app --reload --port 8000
```

Open **http://localhost:8000**, pick a caller, tap the mic, and ask in Hindi or
English — e.g. *"मेरे खाते से पैसे क्यों कटे?"* (Priya) or *"Did my salary come this month?"* (Rajesh).

---

## Project layout
```
sarvamai-elastic/
├── data/
│   ├── knowledge_base.json      # generic KB (semantic)
│   ├── transactions.json        # snapshot of last generated transactions (regenerated each ingest)
│   └── customers.json           # private profiles (+ DOB) & demo callers
├── scripts/
│   ├── 01_create_index.py        # 3 indices, incl. semantic_text mapping
│   ├── generate_transactions.py  # 100+ transactions, dynamic last-30-day dates
│   ├── 02_ingest_data.py         # bulk ingest all three (generates transactions)
│   ├── verify_search.py          # semantic search sanity check
│   └── 03_create_agent.py        # 3 Agent Builder tools + agent
├── backend/
│   ├── sarvam.py                # Sarvam STT / Translate / TTS
│   ├── elastic_agent.py         # Agent Builder converse (SSE)
│   └── app.py                   # FastAPI: /api/voice, /api/text, /api/customers, /api/reset
├── frontend/index.html          # Tailwind UI: caller switcher, mic, pipeline view
├── requirements.txt
├── run_demo.sh
└── .env.example
```

## Demo tips
- The **"behind the scenes"** panel on each reply shows the English query sent
  to Elastic and the agent's English answer — great for narrating the flow.
- Use the **language chips** (Auto / हिंदी / English) to force a language in a
  noisy room; a **typed fallback** works without a mic.
- **↻ New call** re-arms identity verification for the selected caller.
- All secrets live in `.env` (gitignored); nothing is hard-coded.
