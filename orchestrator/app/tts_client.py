import asyncio
import httpx
from .config import KOKORO_URL, VOICE_MAP, TTS_BATCH_SIZE
from .models import ScriptLine


async def _synthesize_one(client: httpx.AsyncClient, text: str, voice: str) -> bytes:
    resp = await client.post(
        f"{KOKORO_URL}/v1/audio/speech",
        json={"model": "kokoro", "input": text, "voice": voice, "response_format": "mp3", "speed": 1.0},
    )
    resp.raise_for_status()
    return resp.content


async def synthesize_lines(
    lines: list[ScriptLine],
    voice_map: dict[str, str] | None = None,
) -> list[bytes]:
    vm = voice_map if voice_map is not None else VOICE_MAP
    results: list[bytes] = []
    async with httpx.AsyncClient(timeout=120) as client:
        for i in range(0, len(lines), TTS_BATCH_SIZE):
            batch = lines[i : i + TTS_BATCH_SIZE]
            batch_results = await asyncio.gather(
                *[_synthesize_one(client, line.text, vm[line.speaker]) for line in batch]
            )
            results.extend(batch_results)
    return results


async def preview_voice(voice: str, name: str) -> bytes:
    """Synthesize a short intro clip used by the UI voice-preview button."""
    text = f"Hello, I'm {name}. I will be your voice for your podcast."
    async with httpx.AsyncClient(timeout=30) as client:
        return await _synthesize_one(client, text, voice)
