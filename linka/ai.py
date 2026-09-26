"""Gemini integration (Google AI Studio / Generative Language API).

Activation: set the GEMINI_API_KEY environment variable and restart Django.
Without a key every helper returns None and callers fall back to the
built-in rule-based logic — the app works fully offline.

Optional: GEMINI_MODEL (default "gemini-2.5-flash").
"""
import hashlib
import json
import os
import urllib.request

GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
TIMEOUT = 25


class RateLimited(Exception):
    """Gemini quota/RPM limit still in force after retries."""


def is_configured() -> bool:
    return bool(os.environ.get("GEMINI_API_KEY"))


def _post_gemini(payload: dict, timeout: int = TIMEOUT) -> dict:
    """POST to generateContent with retry on 429 (honors Retry-After, caps waits)."""
    import time
    import logging
    from urllib.error import HTTPError
    log = logging.getLogger("linka.ai")
    key = os.environ.get("GEMINI_API_KEY", "")
    body = json.dumps(payload).encode()
    waits = [0, 5, 15]  # first attempt immediate, then back off
    last_exc: Exception | None = None
    for attempt, wait in enumerate(waits):
        if wait:
            time.sleep(wait)
        try:
            req = urllib.request.Request(
                f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={key}",
                data=body,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=timeout) as res:
                return json.loads(res.read().decode())
        except HTTPError as exc:
            last_exc = exc
            if exc.code == 429 and attempt < len(waits) - 1:
                retry_after = exc.headers.get("Retry-After") if exc.headers else None
                try:
                    extra = min(int(retry_after), 30)
                except (TypeError, ValueError):
                    extra = 0
                log.warning("Gemini 429, backing off (attempt %d)", attempt + 1)
                if extra:
                    time.sleep(extra)
                continue
            raise
    raise RateLimited(f"Gemini rate-limited after retries: {last_exc}")


def _generate(prompt: str) -> str | None:
    key = os.environ.get("GEMINI_API_KEY", "")
    if not key:
        return None
    try:
        data = _post_gemini({"contents": [{"parts": [{"text": prompt}]}]})
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except RateLimited:
        raise
    except Exception:
        return None


def _parse_json(text: str | None) -> dict | None:
    if not text:
        return None
    try:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`").split("\n", 1)[1].rsplit("```", 1)[0]
        parsed = json.loads(cleaned)
        return parsed if isinstance(parsed, dict) else None
    except Exception:
        return None


INTENT_PROMPT = """You extract structured partnership requirements from a natural-language request.
The request may be in English, French, Portuguese, or Swahili — understand it regardless of language, but always reply with English keywords.
Valid country codes: NG (Nigeria), GH (Ghana), KE (Kenya), RW (Rwanda), ZA (South Africa), EG (Egypt).
Valid industries: Agriculture, Technology, Manufacturing, Logistics, Healthcare, Education, Finance, Creative, Research, Natural resources.
Reply with ONLY a JSON object, no markdown: {"countries": [...], "industries": [...], "keywords": [...]}
Request: %s"""


def extract_intent_llm(query: str) -> dict | None:
    """LLM intent extraction. Returns None when unconfigured/failing (caller falls back)."""
    if not is_configured():
        return None
    try:
        parsed = _parse_json(_generate(INTENT_PROMPT % query[:1000]))
    except RateLimited:
        return None
    if not parsed:
        return None
    valid_countries = {"NG", "GH", "KE", "RW", "ZA", "EG", "OTHER"}
    valid_industries = {"Agriculture", "Technology", "Manufacturing", "Logistics",
                        "Healthcare", "Education", "Finance", "Creative", "Research", "Natural resources"}
    return {
        "countries": sorted({c for c in parsed.get("countries", []) if c in valid_countries}),
        "industries": sorted({i for i in parsed.get("industries", []) if i in valid_industries}),
        "keywords": [str(k) for k in parsed.get("keywords", [])][:12],
    }


def cached_llm_intent(query: str) -> dict | None:
    """LLM intent with a 1h cache on normalized query text.

    Repeat searches (and re-clicks) don't burn extra Gemini calls.
    Returns None on miss/failure so callers fall back to rules.
    """
    from django.core.cache import cache
    normalized = " ".join(query.lower().split())
    key = "intent:" + hashlib.sha256(normalized.encode()).hexdigest()
    hit = cache.get(key)
    if hit is not None:
        return hit
    intent = extract_intent_llm(query)
    if intent is not None:
        cache.set(key, intent, 3600)
    return intent


BRIEF_PROMPT = """You write partnership briefs for African businesses. Write the brief in %s. Reply with ONLY a JSON object, no markdown:
{"opportunity": "2-3 sentences", "benefits": ["...", "...", "..."], "things_to_verify": ["...", "...", "...", "..."]}
Company A (%s, %s) offers: %s. Company B (%s, %s) offers: %s. Objective: %s"""


def generate_brief_llm(company_a: dict, company_b: dict, objective: str, language: str = "English") -> dict | None:
    """LLM partnership brief. Returns None when unconfigured/failing (caller falls back)."""
    if not is_configured():
        return None
    try:
        return _parse_json(_generate(BRIEF_PROMPT % (
            language,
            company_a["name"], company_a["country"], company_a["offers"][:500],
            company_b["name"], company_b["country"], company_b["offers"][:500],
            objective[:300],
        )))
    except RateLimited:
        return None


MOU_PROMPT = """Draft a short non-binding Memorandum of Understanding between two African businesses. Reply with ONLY markdown, no code fences.
Sections: # Parties, ## Purpose, ## Commitments, ## Volumes & Terms, ## Duration, ## Dispute Resolution, ## Signatures (with Not legally binding — requires legal review disclaimer at the end).
Party A: %s (%s) — offers %s. Party B: %s (%s) — offers %s. Partnership type: %s. Context: %s"""


def generate_mou_llm(party_a: dict, party_b: dict, partnership_type: str, context: str) -> str | None:
    if not is_configured():
        return None
    try:
        text = _generate(MOU_PROMPT % (
            party_a["name"], party_a["country"], party_a["offers"][:400],
            party_b["name"], party_b["country"], party_b["offers"][:400],
            partnership_type, context[:400],
        ))
    except RateLimited:
        return None
    return text.strip() if text else None


TRADE_PROMPT = """You are an AfCFTA cross-border trade advisor. Reply with ONLY a JSON object, no markdown:
{"tariff_note": "1-2 sentences on duties/AfCFTA preferences", "certifications": ["...", "..."], "payments": ["...", "..."]}
Trade lane: %s to %s. Goods/sector: %s."""


def generate_trade_llm(from_country: str, to_country: str, industry: str) -> dict | None:
    if not is_configured():
        return None
    try:
        return _parse_json(_generate(TRADE_PROMPT % (from_country, to_country, industry[:200])))
    except RateLimited:
        return None


def transcribe_audio_llm(audio_bytes: bytes, mime: str = "audio/webm") -> str | None:
    """Transcribe a voice note with Gemini (multimodal). Returns plain transcript or None."""
    import base64
    import logging
    log = logging.getLogger("linka.ai")
    key = os.environ.get("GEMINI_API_KEY", "")
    if not key:
        log.warning("voice: no GEMINI_API_KEY configured")
        return None
    if not audio_bytes or len(audio_bytes) < 1024:
        log.warning("voice: audio too short (%d bytes), skipping API call", len(audio_bytes or b""))
        return None
    # Gemini wants a bare mime type — browsers send "audio/webm;codecs=opus"
    mime = (mime or "audio/webm").split(";")[0].strip() or "audio/webm"
    try:
        data = _post_gemini({"contents": [{"parts": [
            {"text": "Transcribe this voice note accurately. Reply with ONLY the transcription, in the speaker's language."},
            {"inline_data": {"mime_type": mime, "data": base64.b64encode(audio_bytes).decode()}},
        ]}]}, timeout=TIMEOUT + 20)
        text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
        if not text:
            log.warning("voice: empty transcript returned")
            return None
        return text
    except RateLimited:
        raise
    except Exception as exc:
        log.warning("voice: transcription failed: %s: %s", type(exc).__name__, str(exc)[:300])
        return None
