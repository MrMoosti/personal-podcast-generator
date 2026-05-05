import io
from pydub import AudioSegment
from .config import PAUSE_SAME_SPEAKER_MS, PAUSE_SPEAKER_CHANGE_MS, LEAD_IN_MS, TAIL_MS
from .models import ScriptLine


def assemble(audio_bytes_list: list[bytes], lines: list[ScriptLine]) -> bytes:
    combined = AudioSegment.silent(duration=LEAD_IN_MS)

    for i, (mp3_bytes, line) in enumerate(zip(audio_bytes_list, lines)):
        combined += AudioSegment.from_mp3(io.BytesIO(mp3_bytes))
        if i < len(lines) - 1:
            next_speaker = lines[i + 1].speaker
            pause_ms = PAUSE_SAME_SPEAKER_MS if next_speaker == line.speaker else PAUSE_SPEAKER_CHANGE_MS
            combined += AudioSegment.silent(duration=pause_ms)

    combined += AudioSegment.silent(duration=TAIL_MS)

    out = io.BytesIO()
    combined.export(out, format="mp3", bitrate="128k")
    return out.getvalue()
