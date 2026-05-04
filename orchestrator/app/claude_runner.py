import asyncio
import json
from .config import CLAUDE_BIN, CLAUDE_MODEL


class ClaudeError(Exception):
    pass


async def run_claude(
    prompt: str,
    *,
    allowed_tools: list[str] | None = None,
    max_turns: int = 1,
    bare: bool = False,
    timeout: int = 300,
) -> str:
    # Pass prompt via stdin to avoid Windows CLI arg length limits (~32k chars)
    cmd = [
        CLAUDE_BIN, "-p", "-",
        "--output-format", "json",
        "--max-turns", str(max_turns),
        "--model", CLAUDE_MODEL,
    ]
    if bare:
        cmd.append("--bare")
    if allowed_tools:
        cmd.extend(["--allowedTools", ",".join(allowed_tools)])

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(input=prompt.encode()), timeout=timeout
        )
    except asyncio.TimeoutError:
        proc.kill()
        raise ClaudeError(f"claude CLI timed out after {timeout}s")

    if proc.returncode != 0:
        raise ClaudeError(f"claude CLI failed (rc={proc.returncode}): {stderr.decode()[:500]}")

    raw = stdout.decode()
    try:
        envelope = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ClaudeError(f"could not parse CLI output: {e}; raw={raw[:500]!r}")

    if envelope.get("subtype") != "success":
        raise ClaudeError(f"claude returned non-success: {envelope}")

    return envelope["result"]


def strip_fences(s: str) -> str:
    s = s.strip()
    if s.startswith("```"):
        parts = s.split("```")
        if len(parts) >= 3:
            s = parts[1]
        if s.startswith("json"):
            s = s[4:]
        s = s.strip()
    return s
