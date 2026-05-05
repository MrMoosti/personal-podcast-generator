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

# All voices available in Kokoro — shown in the UI dropdown
AVAILABLE_VOICES: dict[str, str] = {
    "am_michael": "Michael (American male)",
    "am_adam":    "Adam (American male)",
    "af_bella":   "Bella (American female)",
    "af_nicole":  "Nicole (American female)",
    "af_sarah":   "Sarah (American female)",
    "bf_emma":    "Emma (British female)",
    "bf_isabella":"Isabella (British female)",
    "bm_george":  "George (British male)",
    "bm_lewis":   "Lewis (British male)",
}

# First-name only — used in script personas and voice preview text
VOICE_NAMES: dict[str, str] = {
    "am_michael": "Michael",
    "am_adam":    "Adam",
    "af_bella":   "Bella",
    "af_nicole":  "Nicole",
    "af_sarah":   "Sarah",
    "bf_emma":    "Emma",
    "bf_isabella":"Isabella",
    "bm_george":  "George",
    "bm_lewis":   "Lewis",
}

PAUSE_SAME_SPEAKER_MS = 150
PAUSE_SPEAKER_CHANGE_MS = 350
LEAD_IN_MS = 500
TAIL_MS = 800

CLAUDE_TIMEOUT_RESEARCH = 600   # 10 min
CLAUDE_TIMEOUT_SCRIPT = 300     # 5 min

# Jobs older than this are removed from memory and their MP3s deleted
JOB_MAX_AGE_HOURS = int(os.getenv("JOB_MAX_AGE_HOURS", "24"))
