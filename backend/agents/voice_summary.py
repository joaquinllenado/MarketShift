"""
Voice Summary Agent

Two-stage pipeline:
1. Uses DeepSeek V3 via GMI Cloud to generate a concise, conversational
   narrative summary from the structured pipeline analysis output.
2. Converts the narrative text to speech using ElevenLabs TTS v3 via
   GMI Cloud's async request-queue API, then downloads the audio.

Input:  dict — full pipeline output (product_announcements, funding, etc.)
Output: bytes — MP3 audio of the spoken summary
"""

import json
import logging
import os
import re
import time

import requests as http_requests
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()

logger = logging.getLogger(__name__)

GMI_API_KEY = os.environ.get("GMI_API_KEY", "")
GMI_TTS_BASE = "https://console.gmicloud.ai/api/v1/ie/requestqueue/apikey/requests"
TTS_POLL_INTERVAL = 2
TTS_MAX_WAIT = 120

NARRATIVE_SYSTEM_PROMPT = """\
You are a concise market-intelligence briefing writer. You will receive a JSON
object containing structured competitive-intelligence analysis for a specific
market. Your job is to write a SHORT spoken briefing (aim for 30-60 seconds
when read aloud, roughly 100-180 words).

### Structure your briefing as follows:
1. **Opening** — One sentence framing the market and who was analysed.
2. **Key moves** — 2-3 sentences covering the most important product
   launches, funding rounds, or partnerships.
3. **Opportunities & risks** — 1-2 sentences on the top opportunity and
   the top risk.
4. **Action** — One sentence with the single most important next step.

### Rules
- Write in a natural, conversational tone suitable for audio playback.
- Do NOT use bullet points, numbered lists, markdown, or special formatting.
- Do NOT use abbreviations or acronyms without spelling them out first.
- Avoid filler phrases like "In conclusion" or "To summarize".
- Return ONLY the briefing text. No preamble, no sign-off.\
"""

llm = ChatOpenAI(
    model="deepseek-ai/DeepSeek-V3-0324",
    base_url="https://api.gmi-serving.com/v1",
    api_key=GMI_API_KEY,
    temperature=0.5,
    max_tokens=512,
)


def _strip_thinking(text: str) -> str:
    """Remove DeepSeek R1 <think>…</think> reasoning blocks."""
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()


def _build_summary_input(pipeline_data: dict) -> str:
    """Distill the full pipeline output into a compact JSON payload for the LLM.

    Supports both the analyzed PipelineResponse format (product_announcements,
    funding, etc.) and the raw sub_agent_2 format (web, product_hunt, news,
    aggregated).
    """
    has_analysis = bool(pipeline_data.get("product_announcements"))

    if has_analysis:
        compact = {
            "query": pipeline_data.get("query", ""),
            "product_announcements": [
                {"company": a.get("company"), "title": a.get("title")}
                for a in pipeline_data.get("product_announcements", [])[:5]
            ],
            "funding": [
                {"company": f.get("company"), "title": f.get("title"), "amount": f.get("amount")}
                for f in pipeline_data.get("funding", [])[:5]
            ],
            "partnerships": [
                {"company": p.get("company"), "title": p.get("title")}
                for p in pipeline_data.get("partnerships", [])[:5]
            ],
            "market_signals": [
                {"company": s.get("company"), "title": s.get("title"), "description": s.get("description")}
                for s in pipeline_data.get("market_signals", [])[:5]
            ],
            "market_opportunities": pipeline_data.get("market_opportunities", []),
            "competitive_risks": pipeline_data.get("competitive_risks", []),
            "action_steps": [
                a.get("title") for a in pipeline_data.get("action_steps", [])
            ],
        }
    else:
        items = pipeline_data.get("aggregated", [])
        if not items:
            for src in ("web", "product_hunt", "news"):
                items.extend(pipeline_data.get(src, []))
        compact = {
            "query": pipeline_data.get("query", ""),
            "research_findings": [
                {"title": it.get("title"), "highlights": it.get("highlights", [])[:2]}
                for it in items[:15]
            ],
        }

    return json.dumps(compact, indent=2)


def generate_narrative(pipeline_data: dict) -> str:
    """Generate a natural-language briefing from structured analysis data."""
    user_msg = _build_summary_input(pipeline_data)
    response = llm.invoke([
        {"role": "system", "content": NARRATIVE_SYSTEM_PROMPT},
        {"role": "user", "content": user_msg},
    ])
    return _strip_thinking(response.content)


def _gmi_headers() -> dict:
    return {
        "Authorization": f"Bearer {GMI_API_KEY}",
        "Content-Type": "application/json",
    }


def _submit_tts(text: str, voice_id: str = "21m00Tcm4TlvDq8ikWAM") -> str:
    """Submit a TTS request to GMI Cloud. Returns the request_id."""
    body = {
        "model": "elevenlabs-tts-v3",
        "payload": {
            "text": text,
            "voice_id": voice_id,
            "stability": 0.5,
            "similarity_boost": 0.75,
            "speed": 1.0,
            "use_speaker_boost": True,
            "output_format": "mp3_44100_128",
            "apply_text_normalization": "auto",
        },
    }
    resp = http_requests.post(GMI_TTS_BASE, headers=_gmi_headers(), json=body, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    request_id = data.get("request_id")
    if not request_id:
        raise RuntimeError(f"GMI TTS submit returned no request_id: {data}")
    logger.info("TTS job submitted: %s", request_id)
    return request_id


def _poll_tts(request_id: str) -> str:
    """Poll until the TTS job completes. Returns the audio download URL."""
    url = f"{GMI_TTS_BASE}/{request_id}"
    elapsed = 0.0

    while elapsed < TTS_MAX_WAIT:
        resp = http_requests.get(url, headers=_gmi_headers(), timeout=30)
        resp.raise_for_status()
        data = resp.json()
        status = data.get("status", "")

        if status == "success":
            audio_url = (
                data.get("outcome", {}).get("audio_url")
                or next(
                    (m["url"] for m in data.get("outcome", {}).get("media", []) if m.get("type") == "audio"),
                    None,
                )
            )
            if not audio_url:
                raise RuntimeError(f"TTS succeeded but no audio_url in response: {data}")
            logger.info("TTS job %s completed", request_id)
            return audio_url

        if status == "failed":
            raise RuntimeError(f"TTS job {request_id} failed: {data}")

        if status == "cancelled":
            raise RuntimeError(f"TTS job {request_id} was cancelled")

        time.sleep(TTS_POLL_INTERVAL)
        elapsed += TTS_POLL_INTERVAL

    raise TimeoutError(f"TTS job {request_id} did not complete within {TTS_MAX_WAIT}s")


def _download_audio(audio_url: str) -> bytes:
    """Download the generated audio file."""
    resp = http_requests.get(audio_url, timeout=60)
    resp.raise_for_status()
    return resp.content


def text_to_speech(text: str) -> bytes:
    """Convert text to MP3 audio via ElevenLabs TTS v3 on GMI Cloud."""
    request_id = _submit_tts(text)
    audio_url = _poll_tts(request_id)
    return _download_audio(audio_url)


def generate_voice_summary(pipeline_data: dict) -> bytes:
    """End-to-end: pipeline data -> narrative text -> MP3 audio bytes."""
    narrative = generate_narrative(pipeline_data)
    logger.info("Generated narrative (%d chars): %s...", len(narrative), narrative[:100])
    audio_bytes = text_to_speech(narrative)
    return audio_bytes
