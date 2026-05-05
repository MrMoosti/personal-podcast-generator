import asyncio
import json
import re
import uuid
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import AsyncGenerator

from fastapi import BackgroundTasks, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from sse_starlette.sse import EventSourceResponse

from .audio_assembler import assemble
from .claude_runner import ClaudeError, run_claude, strip_fences
from .config import (
    AVAILABLE_VOICES,
    CLAUDE_TIMEOUT_RESEARCH,
    CLAUDE_TIMEOUT_SCRIPT,
    DATA_DIR,
    JOB_MAX_AGE_HOURS,
    VOICE_NAMES,
)
from .models import GenerationRequest, JobState, PodcastScript, ScriptLine
from .prompts import research_prompt, script_prompt
from .tts_client import preview_voice, synthesize_lines

# ── Helpers ──────────────────────────────────────────────────────────────────

def _slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text[:60].strip("-")


def _voice_name(voice_id: str) -> str:
    return VOICE_NAMES.get(voice_id, voice_id.split("_")[-1].capitalize())


def _voice_map(job: JobState) -> dict[str, str]:
    """Build the speaker-id → Kokoro-voice-id map for a job."""
    vm = {"host": job.request.voices.host}
    for i, voice in enumerate(job.request.voices.experts):
        vm[f"expert_{i}"] = voice
    return vm


def _speaker_names(job: JobState) -> dict[str, str]:
    """Build the speaker-id → display-name map for a job (sent to the UI)."""
    names = {"host": _voice_name(job.request.voices.host)}
    for i, voice in enumerate(job.request.voices.experts):
        names[f"expert_{i}"] = _voice_name(voice)
    return names


# ── Rate-limit detection ─────────────────────────────────────────────────────

_RATE_LIMIT_PHRASES = ("rate limit", "too many requests", "usage limit", "quota exceeded")


def _rate_limit_msg(raw: str) -> str | None:
    if any(p in raw.lower() for p in _RATE_LIMIT_PHRASES):
        return (
            "Claude Pro rate limit reached. "
            "Please wait a few minutes before generating another podcast."
        )
    return None


# ── In-memory state ──────────────────────────────────────────────────────────

jobs: dict[str, JobState] = {}
job_events: dict[str, list[dict]] = {}
job_signals: dict[str, asyncio.Event | None] = {}


def _emit(job_id: str, event: dict) -> None:
    job_events[job_id].append(event)
    sig = job_signals.get(job_id)
    if sig:
        sig.set()


# ── Cleanup task ─────────────────────────────────────────────────────────────

async def _cleanup_loop() -> None:
    while True:
        await asyncio.sleep(3600)
        cutoff = datetime.now(UTC) - timedelta(hours=JOB_MAX_AGE_HOURS)
        stale = [jid for jid, j in list(jobs.items()) if j.updated_at < cutoff]
        for jid in stale:
            job = jobs.pop(jid, None)
            job_events.pop(jid, None)
            job_signals.pop(jid, None)
            if job and job.audio_path:
                Path(job.audio_path).unlink(missing_ok=True)


# ── App lifecycle ─────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(_: FastAPI):
    Path(DATA_DIR).mkdir(parents=True, exist_ok=True)
    asyncio.create_task(_cleanup_loop())
    yield


app = FastAPI(title="Podcast Generator", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Pipeline ──────────────────────────────────────────────────────────────────

async def _synthesize_and_assemble(job_id: str) -> None:
    job = jobs[job_id]
    assert job.script is not None
    lines = job.script.lines

    job.status = "synthesizing"
    job.updated_at = datetime.now(UTC)
    _emit(job_id, {"stage": "synthesizing", "message": f"Synthesizing {len(lines)} audio segments…"})
    try:
        audio_segments = await synthesize_lines(lines, voice_map=_voice_map(job))
    except Exception as e:
        job.status = "error"
        job.error = f"TTS error: {e}"
        job.updated_at = datetime.now(UTC)
        _emit(job_id, {"stage": "error", "message": job.error})
        return

    job.status = "assembling"
    job.updated_at = datetime.now(UTC)
    _emit(job_id, {"stage": "assembling", "message": "Assembling final audio…"})
    try:
        mp3_bytes = assemble(audio_segments, lines)
        audio_path = Path(DATA_DIR) / f"{job_id}.mp3"
        audio_path.write_bytes(mp3_bytes)
        job.audio_path = str(audio_path)
    except Exception as e:
        job.status = "error"
        job.error = f"Assembly error: {e}"
        job.updated_at = datetime.now(UTC)
        _emit(job_id, {"stage": "error", "message": job.error})
        return

    job.status = "done"
    job.updated_at = datetime.now(UTC)
    _emit(job_id, {"stage": "done", "message": "Your podcast is ready!"})


async def _pipeline(job_id: str) -> None:
    job = jobs[job_id]

    # Stage 1: Research
    job.status = "researching"
    job.updated_at = datetime.now(UTC)
    _emit(job_id, {"stage": "researching", "message": "Researching topic on the web…"})
    try:
        research = await run_claude(
            research_prompt(job.request.topic),
            allowed_tools=["WebSearch"],
            max_turns=5,
            timeout=CLAUDE_TIMEOUT_RESEARCH,
        )
    except ClaudeError as e:
        msg = _rate_limit_msg(str(e)) or str(e)
        job.status = "error"
        job.error = msg
        job.updated_at = datetime.now(UTC)
        _emit(job_id, {"stage": "error", "message": msg})
        return

    # Stage 2: Script — pass persona names so Claude uses the right character names
    job.status = "writing"
    job.updated_at = datetime.now(UTC)
    _emit(job_id, {"stage": "writing", "message": "Writing podcast script…"})
    host_name = _voice_name(job.request.voices.host)
    expert_names = [_voice_name(v) for v in job.request.voices.experts]
    try:
        raw = await run_claude(
            script_prompt(
                job.request.topic,
                job.request.duration_minutes,
                research,
                host_name=host_name,
                expert_names=expert_names,
            ),
            max_turns=1,
            timeout=CLAUDE_TIMEOUT_SCRIPT,
        )
    except ClaudeError as e:
        msg = _rate_limit_msg(str(e)) or str(e)
        job.status = "error"
        job.error = msg
        job.updated_at = datetime.now(UTC)
        _emit(job_id, {"stage": "error", "message": msg})
        return

    try:
        data = json.loads(strip_fences(raw))
        lines = [ScriptLine(**ln) for ln in data["lines"]]
        job.script = PodcastScript(
            topic=job.request.topic,
            duration_minutes=job.request.duration_minutes,
            lines=lines,
        )
    except Exception as e:
        job.status = "error"
        job.error = f"Script parse error: {e}"
        job.updated_at = datetime.now(UTC)
        _emit(job_id, {"stage": "error", "message": job.error})
        return

    await _synthesize_and_assemble(job_id)


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/voices")
def list_voices():
    return AVAILABLE_VOICES


@app.get("/api/voices/preview")
async def voice_preview(
    voice: str = Query(..., description="Kokoro voice ID"),
    name: str = Query(..., description="Character name spoken in the sample"),
):
    """Generate a short voice sample and stream it back as MP3."""
    if voice not in AVAILABLE_VOICES:
        raise HTTPException(400, f"Unknown voice: {voice!r}")
    try:
        mp3_bytes = await preview_voice(voice, name)
        return Response(content=mp3_bytes, media_type="audio/mpeg")
    except Exception as e:
        raise HTTPException(500, f"TTS preview failed: {e}")


@app.post("/api/generate")
async def generate(req: GenerationRequest, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    now = datetime.now(UTC)
    jobs[job_id] = JobState(
        job_id=job_id,
        status="pending",
        request=req,
        created_at=now,
        updated_at=now,
    )
    job_events[job_id] = []
    job_signals[job_id] = None
    background_tasks.add_task(_pipeline, job_id)
    return {"job_id": job_id}


@app.post("/api/jobs/{job_id}/regen-audio")
async def regen_audio(job_id: str, background_tasks: BackgroundTasks):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    if not job.script:
        raise HTTPException(400, "No script yet — run /api/generate first")
    if job.status in ("researching", "writing", "synthesizing", "assembling"):
        raise HTTPException(409, "Job is already running")

    if job.audio_path:
        Path(job.audio_path).unlink(missing_ok=True)

    job.status = "pending"
    job.audio_path = None
    job.error = None
    job.updated_at = datetime.now(UTC)
    job_events[job_id] = []
    job_signals[job_id] = None
    background_tasks.add_task(_synthesize_and_assemble, job_id)
    return {"job_id": job_id}


@app.get("/api/jobs/{job_id}/events")
async def stream(job_id: str):
    if job_id not in jobs:
        raise HTTPException(404, "Job not found")

    sig = asyncio.Event()
    job_signals[job_id] = sig

    async def generator() -> AsyncGenerator[dict, None]:
        cursor = 0
        while True:
            sig.clear()
            events = job_events[job_id]
            while cursor < len(events):
                yield {"data": json.dumps(events[cursor])}
                cursor += 1
            if jobs[job_id].status in ("done", "error"):
                break
            try:
                await asyncio.wait_for(sig.wait(), timeout=20)
            except asyncio.TimeoutError:
                yield {"data": json.dumps({"stage": "ping"})}

    return EventSourceResponse(generator())


@app.get("/api/jobs/{job_id}/script")
def get_script(job_id: str):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    if not job.script:
        raise HTTPException(404, "Script not ready")
    # Include speaker_names so the UI can display and export real character names
    return {
        **job.script.model_dump(),
        "speaker_names": _speaker_names(job),
    }


@app.get("/api/jobs/{job_id}/audio")
def get_audio(job_id: str):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    if not job.audio_path:
        raise HTTPException(404, "Audio not ready")
    p = Path(job.audio_path)
    if not p.exists():
        raise HTTPException(404, "Audio file missing")
    filename = f"{_slugify(job.request.topic)}.mp3"
    return FileResponse(str(p), media_type="audio/mpeg", filename=filename)
