from pydantic import BaseModel, Field
from typing import Literal
from datetime import datetime

# Speaker is now a free string ("host", "expert_0", "expert_1", …)
Speaker = str
Segment = Literal["intro", "main", "qa", "outro"]
JobStatus = Literal["pending", "researching", "writing", "synthesizing", "assembling", "done", "error"]


class VoiceConfig(BaseModel):
    host: str = "am_michael"
    experts: list[str] = ["bf_emma"]   # 1–3 expert voices


class GenerationRequest(BaseModel):
    topic: str = Field(min_length=3, max_length=300)
    duration_minutes: Literal[5, 10, 15, 20]
    voices: VoiceConfig = VoiceConfig()


class ScriptLine(BaseModel):
    speaker: Speaker
    text: str
    segment: Segment


class PodcastScript(BaseModel):
    topic: str
    duration_minutes: int
    lines: list[ScriptLine]
    sources: list[str] = []


class JobState(BaseModel):
    job_id: str
    status: JobStatus
    request: GenerationRequest
    script: PodcastScript | None = None
    audio_path: str | None = None
    error: str | None = None
    created_at: datetime
    updated_at: datetime
