"""
Thin client for the three Sarvam AI REST APIs used in this demo:

  - Speech-to-Text       POST /speech-to-text        (saaras:v3 / saarika:v2.5)
  - Text Translation     POST /translate             (mayura:v1)
  - Text-to-Speech       POST /text-to-speech        (bulbul:v2 / bulbul:v3)

Docs: https://docs.sarvam.ai
"""
import io
import os
import re
import base64
import struct
import requests

SARVAM_BASE = "https://api.sarvam.ai"
TTS_CHUNK_LIMIT = 500   # chars per TTS API call (well inside bulbul:v2 limit)


class SarvamClient:
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.environ["SARVAM_API_KEY"]
        self.stt_model = os.getenv("SARVAM_STT_MODEL", "saaras:v3")
        self.translate_model = os.getenv("SARVAM_TRANSLATE_MODEL", "mayura:v1")
        self.tts_model = os.getenv("SARVAM_TTS_MODEL", "bulbul:v2")
        self.tts_speaker = os.getenv("SARVAM_TTS_SPEAKER", "anushka")
        # Grammatical gender of the speaker (the assistant) — drives gendered
        # verb forms in the translation, e.g. Hindi "raha hoon" (Male) vs
        # "rahi hoon" (Female). Keep this aligned with the TTS voice.
        self.speaker_gender = os.getenv("SARVAM_SPEAKER_GENDER", "Male")

    @property
    def _key_header(self):
        return {"api-subscription-key": self.api_key}

    # ── Speech to Text ────────────────────────────────────────────────
    def speech_to_text(self, audio_bytes: bytes, filename: str = "audio.wav",
                       content_type: str = "audio/wav") -> dict:
        files = {"file": (filename, audio_bytes, content_type)}
        data = {"model": self.stt_model}
        if self.stt_model.startswith("saaras"):
            data["mode"] = "transcribe"
        else:
            data["language_code"] = "unknown"
        r = requests.post(
            f"{SARVAM_BASE}/speech-to-text",
            headers=self._key_header,
            files=files,
            data=data,
            timeout=60,
        )
        r.raise_for_status()
        return r.json()

    # ── Text Translation ──────────────────────────────────────────────
    def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        """Translate text between Indian languages / English (BCP-47 codes)."""
        if not text.strip() or source_lang == target_lang:
            return text
        # mayura:v1 accepts up to 1000 chars; split longer text into chunks
        chunks = self._split_text(text, 950)
        translated = []
        for chunk in chunks:
            payload = {
                "input": chunk,
                "source_language_code": source_lang,
                "target_language_code": target_lang,
                "model": self.translate_model,
                "mode": "formal",
                "speaker_gender": self.speaker_gender,
            }
            r = requests.post(
                f"{SARVAM_BASE}/translate",
                headers={**self._key_header, "Content-Type": "application/json"},
                json=payload,
                timeout=30,
            )
            r.raise_for_status()
            translated.append(r.json()["translated_text"])
        return " ".join(translated)

    # ── Text to Speech ────────────────────────────────────────────────
    _INDIC_LANGS = {"hi-IN", "mr-IN", "gu-IN", "bn-IN", "pa-IN", "ta-IN", "te-IN", "kn-IN", "ml-IN"}

    @staticmethod
    def _normalize_for_tts(text: str, lang: str) -> str:
        """Make text more TTS-friendly for Indic languages."""
        if lang in SarvamClient._INDIC_LANGS:
            # Replace ₹ with the spoken word so TTS doesn't skip it
            text = re.sub(r'₹\s*', 'रुपये ', text)
            # Remove commas inside numbers (e.g. 4,416 → 4416) so TTS reads them cleanly
            text = re.sub(r'(\d),(\d)', r'\1\2', text)
        return text

    @staticmethod
    def _strip_markdown(text: str) -> str:
        text = re.sub(r'\*{1,3}(.+?)\*{1,3}', r'\1', text, flags=re.S)
        text = re.sub(r'_{1,2}(.+?)_{1,2}', r'\1', text, flags=re.S)
        text = re.sub(r'#+\s*', '', text)
        text = re.sub(r'`+(.+?)`+', r'\1', text, flags=re.S)
        text = re.sub(r'\[(.+?)\]\(.+?\)', r'\1', text)
        text = re.sub(r'^\s*[-*>]\s+', '', text, flags=re.M)
        text = re.sub(r'[*_`#~]+', '', text)
        return text.strip()

    @staticmethod
    def _split_text(text: str, limit: int) -> list[str]:
        """Split text into chunks at sentence boundaries, each under `limit` chars."""
        if len(text) <= limit:
            return [text]
        chunks, current = [], []
        current_len = 0
        # split on sentence-ending punctuation
        for sentence in re.split(r'(?<=[.?!।])\s+', text):
            if current_len + len(sentence) > limit and current:
                chunks.append(" ".join(current))
                current, current_len = [], 0
            # if a single sentence is too long, hard-split it
            while len(sentence) > limit:
                chunks.append(sentence[:limit])
                sentence = sentence[limit:]
            current.append(sentence)
            current_len += len(sentence) + 1
        if current:
            chunks.append(" ".join(current))
        return chunks

    @staticmethod
    def _join_wavs(wav_b64_list: list[str]) -> str:
        """Concatenate multiple base64 WAV strings into one valid base64 WAV."""
        if len(wav_b64_list) == 1:
            return wav_b64_list[0]
        raw_chunks = [base64.b64decode(b) for b in wav_b64_list]
        # WAV header is 44 bytes for standard PCM; extract PCM data from each
        pcm_data = b"".join(w[44:] for w in raw_chunks)
        # rebuild a valid WAV header from the first chunk, updated data size
        header = bytearray(raw_chunks[0][:44])
        data_size = len(pcm_data)
        struct.pack_into("<I", header, 4, 36 + data_size)   # RIFF chunk size
        struct.pack_into("<I", header, 40, data_size)        # data sub-chunk size
        combined = bytes(header) + pcm_data
        return base64.b64encode(combined).decode()

    def text_to_speech(self, text: str, target_lang: str) -> str:
        """
        Convert text to speech, splitting long texts into chunks so nothing
        is truncated. Returns a single base64-encoded WAV string.
        """
        clean = self._strip_markdown(text)
        clean = self._normalize_for_tts(clean, target_lang)
        chunks = self._split_text(clean, TTS_CHUNK_LIMIT)
        wav_parts = []
        for chunk in chunks:
            if not chunk.strip():
                continue
            payload = {
                "text": chunk,
                "target_language_code": target_lang,
                "speaker": self.tts_speaker,
                "model": self.tts_model,
            }
            r = requests.post(
                f"{SARVAM_BASE}/text-to-speech",
                headers={**self._key_header, "Content-Type": "application/json"},
                json=payload,
                timeout=60,
            )
            r.raise_for_status()
            audios = r.json().get("audios", [])
            wav_parts.extend(audios)
        if not wav_parts:
            return ""
        return self._join_wavs(wav_parts)
