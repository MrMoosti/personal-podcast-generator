<div align="center">

# 🎙️ Personal Podcast Generator

**Turn any topic into a polished, multi-voice podcast — powered by your Claude Pro subscription and a local GPU. No API key. No cloud. No extra billing.**

[![Docker](https://img.shields.io/badge/Docker-compose-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)
[![Next.js](https://img.shields.io/badge/Next.js-15-black?logo=next.js)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://python.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5-3178C6?logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![Claude Pro](https://img.shields.io/badge/Claude_Pro-required-D97706?logo=anthropic&logoColor=white)](https://claude.ai/)
[![GPU](https://img.shields.io/badge/NVIDIA-GPU%20required-76B900?logo=nvidia&logoColor=white)](https://developer.nvidia.com/cuda-toolkit)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

<br/>

> *Type a topic. Pick your voices. Get a real podcast — research, script, and audio — in minutes.*

<br/>

```
 ╔═══════════════════════════════════════════════════════╗
 ║  Topic:  "How quantum computers actually work"        ║
 ║  Length: 15 minutes   Voices: Michael + Emma          ║
 ║                                                       ║
 ║  [Researching...]  ████████░░░░░  Claude searches web ║
 ║  [Writing...]      ████████████░  Script generated    ║
 ║  [Synthesizing...] ████░░░░░░░░░  Kokoro TTS (GPU)    ║
 ║  [Done!] ▶ Play   ⬇ Download MP3   📄 Get script     ║
 ╚═══════════════════════════════════════════════════════╝
```

</div>

---

## ✨ What You Get

| Feature | Details |
|---------|---------|
| 🧠 **AI Research** | Claude searches the web and builds a fact-checked brief on your topic |
| 📝 **Smart Scripting** | Two-persona dialogue (host + 1–3 experts) with intro, deep-dive, Q&A, and outro |
| 🎤 **Local TTS** | GPU-accelerated [Kokoro](https://github.com/remsky/kokoro-fastapi) — 9 natural voices, no cloud calls |
| 📡 **Live Progress** | Server-Sent Events stream updates in real time |
| 🔄 **Regenerate Audio** | Swap voices and re-synthesize without re-running Claude |
| ⬇️ **Dual Download** | MP3 audio + Markdown script, both from the browser |
| 🔒 **100% Private** | Everything runs on your machine — no data leaves your network |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                  Browser  localhost:3000                         │
│              Next.js 15 · React 18 · Tailwind CSS               │
└────────────────────────┬────────────────────────────────────────┘
                         │  REST + Server-Sent Events
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│             FastAPI Orchestrator  localhost:8000                 │
│                                                                 │
│  1. Research  → claude -p (WebSearch tool, 10 min timeout)      │
│  2. Write     → claude -p (JSON script, 5 min timeout)          │
│  3. Synthesize→ Kokoro HTTP · 4 lines in parallel               │
│  4. Assemble  → pydub · lead-in / pauses / tail → MP3           │
└────────────┬─────────────────────────────┬──────────────────────┘
             │                             │
             ▼                             ▼
┌─────────────────────┐     ┌───────────────────────────────────┐
│   Claude CLI (Pro)  │     │   Kokoro TTS  localhost:8880      │
│   Auth via mounted  │     │   GPU-accelerated · OpenAI API    │
│   ~/.claude/        │     │   compatible · ~1 GB VRAM         │
└─────────────────────┘     └───────────────────────────────────┘
```

**Jobs** are held in memory (auto-purged after 24 h). **Audio files** live in `./data/` on your host and persist across container restarts.

---

## 📋 Prerequisites

| Requirement | Why |
|-------------|-----|
| **Docker Desktop** with WSL2 backend | Runs all three services |
| **NVIDIA GPU** (RTX recommended) | Kokoro TTS needs ~1 GB VRAM |
| **NVIDIA Container Toolkit** | GPU passthrough into Docker — [install guide](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html) |
| **Node.js 18+** | To install the Claude CLI globally |
| **Claude Pro subscription** | Powers research + script generation via `claude -p` (no API key needed) |

---

## 🚀 Getting Started

### Step 1 — Install the Claude CLI

Open **Command Prompt** (not PowerShell — avoids execution-policy issues):

```cmd
npm install -g @anthropic-ai/claude-code
```

### Step 2 — Authenticate

```cmd
claude login
```

A browser window opens. Sign in with the account that holds your **Claude Pro** subscription.  
Credentials are saved to `%USERPROFILE%\.claude\` and `%USERPROFILE%\.claude.json`.

### Step 3 — Enable GPU in Docker Desktop

> Docker Desktop → **Settings** → **Resources** → tick **Enable GPU** (requires WSL2 backend)

### Step 4 — Clone & Launch

```cmd
git clone https://github.com/MrMoosti/personal-podcast-generator.git
cd personal-podcast-generator
docker compose up --build
```

> **First run:** Kokoro downloads its model weights (~500 MB). Wait until all three services log `Application startup complete` before opening the app.

### Step 5 — Open the App

**→ [http://localhost:3000](http://localhost:3000)**

---

## 🎧 Usage

```
1.  Type a topic        →  "How nuclear fusion reactors work"
2.  Pick a duration     →  5 / 10 / 15 / 20 minutes
3.  Expand Voice settings  (optional)
     • Choose a host voice  (default: Michael)
     • Add up to 3 expert voices  (default: Emma)
     • Click 🔊 to preview any voice before generating
4.  Hit  Generate Podcast
5.  Watch live progress:  Researching → Writing → Synthesizing → Assembling
6.  Play in-browser  ▶  or  ⬇ Download MP3 / Markdown script
```

**Pro tip — Regenerate Audio:** After a podcast is done, change the voices and click **Regenerate Audio** to re-synthesize without re-running the (costly) research and writing steps. Great for finding your favourite voice combination.

---

## 🎤 Available Voices

| Voice ID | Name | Accent | Gender |
|----------|------|--------|--------|
| `am_michael` | Michael | American | Male · *default host* |
| `am_adam` | Adam | American | Male |
| `af_bella` | Bella | American | Female |
| `af_nicole` | Nicole | American | Female |
| `af_sarah` | Sarah | American | Female |
| `bf_emma` | Emma | British | Female · *default expert* |
| `bf_isabella` | Isabella | British | Female |
| `bm_george` | George | British | Male |
| `bm_lewis` | Lewis | British | Male |

Click the **🔊 preview** button next to any voice in the UI to hear a short sample before committing.

---

## ⚙️ Configuration

Copy `.env.example` to `.env` to override defaults:

```dotenv
# URL of the Kokoro TTS service (set automatically by docker compose)
KOKORO_URL=http://localhost:8880

# Claude model to use ("sonnet", "opus", "haiku")
CLAUDE_MODEL=sonnet

# Name of the Claude CLI binary (must be on PATH inside the container)
CLAUDE_BIN=claude

# Directory where finished MP3 files are stored
DATA_DIR=./data
```

The web frontend's API endpoint is set at **build time** via `NEXT_PUBLIC_API_URL` (default: `http://localhost:8000`). Override it in `docker-compose.yml` if you expose the orchestrator on a different host.

---

## 🔧 Troubleshooting

<details>
<summary><strong>Auth errors / <code>claude login</code> fails</strong></summary>

The orchestrator container mounts two items from your host (read-only):

```
%USERPROFILE%\.claude\      →  /root/.claude/
%USERPROFILE%\.claude.json  →  /root/.claude.json
```

If `.claude.json` is missing, restore it from the CLI's automatic backup:

```cmd
copy "%USERPROFILE%\.claude\backups\.claude.json.backup.*" "%USERPROFILE%\.claude.json"
```

Then restart the orchestrator:

```cmd
docker compose restart orchestrator
```
</details>

<details>
<summary><strong>Kokoro won't start or shows GPU errors</strong></summary>

1. Confirm Docker Desktop has GPU enabled: **Settings → Resources → GPU**
2. Verify the NVIDIA Container Toolkit is installed in your WSL2 distro
3. Quick sanity check:
   ```cmd
   docker run --rm --gpus all nvidia/cuda:12.0-base nvidia-smi
   ```
   You should see your GPU listed. If not, revisit the [Container Toolkit install guide](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html).
</details>

<details>
<summary><strong>Rate limit error during generation</strong></summary>

Claude Pro operates on a rolling 5-hour usage window. Each podcast generation makes **two Claude calls** (research + script writing). Heavy back-to-back generation can exhaust the window quickly.

Wait for the window to reset, then try again. The app catches the rate-limit response and displays a clear message with an estimated wait time.
</details>

<details>
<summary><strong>Audio is silent or corrupt</strong></summary>

Kokoro may still be loading its model on first use. Check:

```cmd
docker compose logs kokoro
```

Wait for it to finish downloading model weights before triggering generation. The orchestrator's `/health` endpoint and the Kokoro log both signal when the service is ready.
</details>

<details>
<summary><strong>Job disappears after container restart</strong></summary>

Jobs are stored in memory — they do not survive a container restart. Audio files in `./data/` **do** persist (they're on a host-mounted volume), but the job entry needed to play/download them via the UI is gone. This is by design to keep the stack simple. Re-generate if you need a fresh job reference.
</details>

---

## 🌐 API Reference

The orchestrator exposes a small REST + SSE API at `http://localhost:8000`:

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check |
| `GET` | `/api/voices` | List all available voice options |
| `GET` | `/api/voices/preview` | Stream a short voice sample MP3 |
| `POST` | `/api/generate` | Submit a new podcast generation job |
| `GET` | `/api/jobs/{id}/events` | SSE stream — live status updates |
| `GET` | `/api/jobs/{id}/script` | Fetch the generated script (JSON) |
| `GET` | `/api/jobs/{id}/audio` | Download the finished MP3 |
| `POST` | `/api/jobs/{id}/regen-audio` | Re-synthesize audio with new voices |

Interactive docs are available at **[http://localhost:8000/docs](http://localhost:8000/docs)** while the stack is running.

---

## 📦 Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | Next.js 15, React 18, TypeScript, Tailwind CSS |
| **Backend** | Python 3.12, FastAPI, uvicorn, sse-starlette |
| **Audio processing** | pydub + ffmpeg |
| **TTS** | Kokoro FastAPI (GPU), OpenAI-compatible endpoint |
| **AI** | Claude Pro via Claude CLI (`claude -p`) |
| **Infrastructure** | Docker Compose (3 services) |

---

## ⭐ Star History

<div align="center">

[![Star History Chart](https://api.star-history.com/svg?repos=MrMoosti/personal-podcast-generator&type=Date)](https://star-history.com/#MrMoosti/personal-podcast-generator&Date)

</div>

---

## 🤝 Contributing

Pull requests are welcome. For major changes, open an issue first to discuss what you'd like to change.

```
git clone https://github.com/MrMoosti/personal-podcast-generator.git
cd personal-podcast-generator

# Run the orchestrator locally (no Docker needed for backend dev)
cd orchestrator
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Run the frontend locally
cd ../web
npm install
npm run dev
```

---

## 📄 License

[MIT](LICENSE) — do whatever you like, attribution appreciated.

---

<div align="center">

Built with ❤️ using [Claude](https://claude.ai) · [Kokoro TTS](https://github.com/remsky/kokoro-fastapi) · [FastAPI](https://fastapi.tiangolo.com) · [Next.js](https://nextjs.org)

</div>
