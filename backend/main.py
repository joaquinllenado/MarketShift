import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from schemas import PipelineRequest, PipelineResponse

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="MarketShift API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    import time as _time

    start = _time.perf_counter()
    logger.info("→  %s %s", request.method, request.url.path)
    response = await call_next(request)
    elapsed_ms = (_time.perf_counter() - start) * 1000
    logger.info("←  %s %s  %d  (%.0f ms)", request.method, request.url.path, response.status_code, elapsed_ms)
    return response


# --- FastAPI endpoints ---

RESULTS_PATH = Path(__file__).parent / "data" / "results.json"

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/pipeline", response_model=PipelineResponse)
def pipeline(request: PipelineRequest):
    url = request.url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="url must not be empty.")
    logger.info("Pipeline started for URL: %s", url)

    from agents.orchestrator import run_pipeline
    result = run_pipeline(url)

    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = result if isinstance(result, dict) else result.model_dump()
    payload["persisted_at"] = datetime.now(timezone.utc).isoformat()
    RESULTS_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    logger.info("Pipeline complete — results persisted to %s", RESULTS_PATH)
    return payload


@app.post("/pipeline/voice-summary")
def voice_summary():
    if not RESULTS_PATH.exists():
        logger.warning("Voice summary requested but no pipeline results exist")
        raise HTTPException(status_code=404, detail="No pipeline results found. Run the pipeline first.")

    logger.info("Generating voice summary from %s", RESULTS_PATH)
    raw = json.loads(RESULTS_PATH.read_text(encoding="utf-8"))
    pipeline_data = raw[-1] if isinstance(raw, list) else raw

    from agents.voice_summary import generate_voice_summary
    try:
        audio_bytes = generate_voice_summary(pipeline_data)
    except Exception as exc:
        logger.exception("Voice summary generation failed")
        raise HTTPException(status_code=502, detail=f"Voice summary generation failed: {exc}")

    audio_path = RESULTS_PATH.parent / "voice_summary.mp3"
    audio_path.write_bytes(audio_bytes)
    logger.info("Voice summary saved to %s", audio_path)

    return Response(
        content=audio_bytes,
        media_type="audio/mpeg",
        headers={"Content-Disposition": "inline; filename=market_briefing.mp3"},
    )
