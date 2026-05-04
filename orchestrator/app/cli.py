"""
CLI runner for Phase 1 testing.
Usage: python -m app.cli "topic" <duration_minutes>
Example: python -m app.cli "How React Server Components work" 10
"""
import asyncio
import json
import sys
from pathlib import Path

from .claude_runner import run_claude, strip_fences, ClaudeError
from .prompts import research_prompt, script_prompt
from .config import CLAUDE_TIMEOUT_RESEARCH, CLAUDE_TIMEOUT_SCRIPT


async def generate_script(topic: str, duration_minutes: int) -> dict:
    print(f"[1/2] Researching: {topic!r} ...")
    try:
        research = await run_claude(
            research_prompt(topic),
            allowed_tools=["WebSearch"],
            max_turns=5,
            bare=False,
            timeout=CLAUDE_TIMEOUT_RESEARCH,
        )
    except ClaudeError as e:
        print(f"Research failed: {e}", file=sys.stderr)
        raise

    print(f"[2/2] Writing script (~{140 * duration_minutes} words) ...")
    try:
        raw_script = await run_claude(
            script_prompt(topic, duration_minutes, research),
            max_turns=1,
            bare=False,
            timeout=CLAUDE_TIMEOUT_SCRIPT,
        )
    except ClaudeError as e:
        print(f"Script generation failed: {e}", file=sys.stderr)
        raise

    cleaned = strip_fences(raw_script)
    try:
        script = json.loads(cleaned)
    except json.JSONDecodeError as e:
        print(f"JSON parse failed: {e}\nRaw output:\n{raw_script[:1000]}", file=sys.stderr)
        raise

    return {
        "topic": topic,
        "duration_minutes": duration_minutes,
        "lines": script["lines"],
        "research_brief": research,
    }


def main():
    if len(sys.argv) < 3:
        print("Usage: python -m app.cli <topic> <duration_minutes>")
        print("Example: python -m app.cli \"React Server Components\" 10")
        sys.exit(1)

    topic = sys.argv[1]
    try:
        duration = int(sys.argv[2])
    except ValueError:
        print(f"duration_minutes must be an integer, got: {sys.argv[2]}", file=sys.stderr)
        sys.exit(1)

    if duration not in (5, 10, 15, 20):
        print(f"duration_minutes must be 5, 10, 15, or 20, got: {duration}", file=sys.stderr)
        sys.exit(1)

    result = asyncio.run(generate_script(topic, duration))

    out_path = Path(f"script_{topic[:30].replace(' ', '_')}.json")
    out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nDone. Script saved to: {out_path}")
    print(f"Lines: {len(result['lines'])}")

    speakers = [l["speaker"] for l in result["lines"]]
    segments = [l["segment"] for l in result["lines"]]
    print(f"Host lines: {speakers.count('host')}, Expert lines: {speakers.count('expert')}")
    print(f"Segments: intro={segments.count('intro')}, main={segments.count('main')}, qa={segments.count('qa')}, outro={segments.count('outro')}")


if __name__ == "__main__":
    main()
