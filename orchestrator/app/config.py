import os

KOKORO_URL = os.getenv("KOKORO_URL", "http://localhost:8880")
DATA_DIR = os.getenv("DATA_DIR", "./data")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "sonnet")
CLAUDE_BIN = os.getenv("CLAUDE_BIN", "claude")

WORDS_PER_MINUTE = 140
QA_FRACTION = 0.25
TTS_BATCH_SIZE = 4

VOICE_MAP = {
    "host": "am_michael",
    "expert": "bf_emma",
}

PAUSE_SAME_SPEAKER_MS = 150
PAUSE_SPEAKER_CHANGE_MS = 350
LEAD_IN_MS = 500
TAIL_MS = 800

CLAUDE_TIMEOUT_RESEARCH = 600
CLAUDE_TIMEOUT_SCRIPT = 300
