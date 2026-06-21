"""
Pratham Bank Voice Agent — FastAPI backend ("Where is my money?").

Pipeline for one voice turn:
  1. STT       Sarvam /speech-to-text  -> caller's words + detected language
  2. Translate Sarvam /translate        -> English query (Elastic is queried in English)
  3. Agent     Elastic Agent Builder    -> verifies identity (DOB) on first turn,
                                           then answers from the caller's own
                                           transactions (private) or the generic
                                           knowledge base
  4. Translate Sarvam /translate        -> answer back in the caller's language
  5. TTS       Sarvam /text-to-speech    -> spoken reply (base64 WAV)

The authenticated caller (a "logged-in" demo customer) is passed as trusted
context to the agent, which scopes every data lookup to that customer_id and
verifies the caller's date of birth before disclosing any money details.
A per-customer conversation id is kept so verification persists within a call.
"""
import os
import json
import time
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

from sarvam import SarvamClient
from elastic_agent import AgentBuilderClient

load_dotenv()

HERE = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(HERE, "..", "frontend")
DATA_DIR = os.path.join(HERE, "..", "data")
EN = "en-IN"

app = FastAPI(title="Pratham Bank Voice Agent")
sarvam = SarvamClient()
agent = AgentBuilderClient()

# Demo customers (the "logged-in" callers). DOB stays server-side / as a demo hint.
with open(os.path.join(DATA_DIR, "customers.json"), encoding="utf-8") as f:
    CUSTOMERS = {c["customer_id"]: c for c in json.load(f)}

# In-memory conversation store so identity verification persists within a call.
# session key = customer_id  ->  Agent Builder conversation_id
SESSIONS: dict[str, str] = {}


def _lang(code: str | None) -> str:
    return EN if not code or code in ("unknown", "null") else code


def _caller(customer_id: str) -> dict:
    cust = CUSTOMERS.get(customer_id)
    if not cust:
        raise HTTPException(400, f"Unknown customer_id '{customer_id}'")
    return cust



def _agent_input(cust: dict, query_en: str) -> str:
    return (
        f"[AUTHENTICATED CALLER — customer_id={cust['customer_id']}, "
        f"name={cust['name']}, account ending {cust['account_last4']}. "
        f"Use ONLY this customer_id for any data lookup. Verify the caller's "
        f"date of birth before sharing balance or transaction details.]\n\n"
        f"Customer says: {query_en}"
    )


def _prepare_audio(audio_bytes: bytes, content_type: str) -> tuple[bytes, str, str]:
    """Return (audio_bytes, filename, content_type) ready to send to Sarvam STT.
    Sarvam accepts webm, ogg, mp4, wav natively — no conversion needed."""
    if "ogg" in content_type:
        return audio_bytes, "audio.ogg", content_type
    if "mp4" in content_type or "m4a" in content_type:
        return audio_bytes, "audio.mp4", content_type
    # default: webm (most browsers)
    return audio_bytes, "audio.webm", "audio/webm"


def _run(cust: dict, query_en: str) -> dict:
    conv = SESSIONS.get(cust["customer_id"])
    result = agent.ask(_agent_input(cust, query_en), conversation_id=conv)
    if result.get("conversation_id"):
        SESSIONS[cust["customer_id"]] = result["conversation_id"]
    return result


@app.get("/api/health")
def health():
    return {"status": "ok", "agent_id": agent.agent_id}


@app.get("/api/customers")
def customers():
    """Demo login switcher data (DOB shown only as a presenter hint)."""
    return [
        {
            "customer_id": c["customer_id"],
            "name": c["name"],
            "city": c["city"],
            "account_last4": c["account_last4"],
            "products": c["products"],
            "preferred_language": c.get("preferred_language", EN),
            "dob_hint": c["dob_display"],
            "hook": c.get("hook", ""),
        }
        for c in CUSTOMERS.values()
    ]


@app.post("/api/reset")
def reset(customer_id: str = Form(...)):
    """Start a fresh call (clears the conversation so identity is re-verified)."""
    SESSIONS.pop(customer_id, None)
    return {"status": "reset", "customer_id": customer_id}


@app.post("/api/voice")
async def voice(file: UploadFile = File(...), customer_id: str = Form(...),
               force_language: str = Form("")):
    cust = _caller(customer_id)
    audio = await file.read()
    if not audio:
        raise HTTPException(400, "Empty audio upload")
    try:
        c = time.perf_counter
        t, t0 = {}, time.perf_counter()
        ct = file.content_type or "audio/webm"
        audio_data, fname, fct = _prepare_audio(audio, ct)

        s = c(); stt = sarvam.speech_to_text(audio_data, fname, fct); t["stt"] = c() - s
        transcript = (stt.get("transcript") or "").strip()
        lang = _lang(force_language or stt.get("language_code"))
        if not transcript:
            raise HTTPException(422, "Could not transcribe audio. Please try again.")

        s = c(); query_en = sarvam.translate(transcript, lang, EN) if lang != EN else transcript; t["translate_in"] = c() - s
        s = c(); result = _run(cust, query_en); t["agent"] = c() - s
        answer_en = result["answer"] or "I'm sorry, I could not find that. Please call customer care at 1800-123-4567."
        s = c(); answer_local = sarvam.translate(answer_en, EN, lang) if lang != EN else answer_en; t["translate_out"] = c() - s
        s = c(); audio_b64 = sarvam.text_to_speech(answer_local, lang); t["tts"] = c() - s
        t["total"] = c() - t0
        print("⏱  /api/voice  " + "  ".join(f"{k}={v:.2f}s" for k, v in t.items()))

        return JSONResponse({
            "customer": {"id": cust["customer_id"], "name": cust["name"]},
            "detected_language": lang,
            "transcript": transcript,
            "query_en": query_en,
            "answer_en": answer_en,
            "answer_local": answer_local,
            "audio_base64": audio_b64,
            "timings": {k: round(v, 2) for k, v in t.items()},
        })
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(502, f"Pipeline error: {type(e).__name__}: {e}")


@app.post("/api/text")
async def text(message: str = Form(...), customer_id: str = Form(...),
              language: str = Form("en-IN")):
    cust = _caller(customer_id)
    lang = _lang(language)
    try:
        c = time.perf_counter
        t, t0 = {}, time.perf_counter()
        s = c(); query_en = sarvam.translate(message, lang, EN) if lang != EN else message; t["translate_in"] = c() - s
        s = c(); result = _run(cust, query_en); t["agent"] = c() - s
        answer_en = result["answer"] or "I'm sorry, I could not find that."
        s = c(); answer_local = sarvam.translate(answer_en, EN, lang) if lang != EN else answer_en; t["translate_out"] = c() - s
        s = c(); audio_b64 = sarvam.text_to_speech(answer_local, lang); t["tts"] = c() - s
        t["total"] = c() - t0
        print("⏱  /api/text   " + "  ".join(f"{k}={v:.2f}s" for k, v in t.items()))
        return JSONResponse({
            "customer": {"id": cust["customer_id"], "name": cust["name"]},
            "detected_language": lang,
            "transcript": message,
            "query_en": query_en,
            "answer_en": answer_en,
            "answer_local": answer_local,
            "audio_base64": audio_b64,
            "timings": {k: round(v, 2) for k, v in t.items()},
        })
    except Exception as e:
        raise HTTPException(502, f"Pipeline error: {type(e).__name__}: {e}")


@app.get("/")
def index():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))


if os.path.isdir(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")
