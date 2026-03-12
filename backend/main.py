import logging
from datetime import datetime, timezone

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

app = FastAPI(title="MarketShift API", version="1.0.1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "https://market-shift-ngh2.vercel.app", "https://marketshift.vercel.app/"],
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

    payload = result if isinstance(result, dict) else result.model_dump()
    payload["persisted_at"] = datetime.now(timezone.utc).isoformat()

    logger.info("Pipeline complete")
    return payload


@app.post("/pipeline/voice-summary")
def voice_summary(pipeline_data: PipelineResponse):
    """Generate voice summary from pipeline result. Client sends the pipeline response in the POST body."""
    logger.info("Generating voice summary from request body")

    from agents.voice_summary import generate_voice_summary
    try:
        audio_bytes = generate_voice_summary(pipeline_data.model_dump())
    except Exception as exc:
        logger.exception("Voice summary generation failed")
        raise HTTPException(status_code=502, detail=f"Voice summary generation failed: {exc}")

    return Response(
        content=audio_bytes,
        media_type="audio/mpeg",
        headers={"Content-Disposition": "inline; filename=market_briefing.mp3"},
    )


#test commit comment
#test commit comment 2