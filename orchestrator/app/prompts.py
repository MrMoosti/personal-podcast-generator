def research_prompt(topic: str) -> str:
    return f"""You are a research assistant preparing background material for a podcast episode.

Topic: {topic}

Search the web and produce a comprehensive research brief covering:
1. Core concepts and definitions
2. How it works (mechanisms, architecture, key components)
3. Common use cases and real-world examples
4. Recent developments or news (last 12 months if relevant)
5. Common pitfalls or misconceptions
6. 3-5 source URLs you used

Format your response as structured markdown. Be specific and factual. Include concrete examples.
Do not write the podcast script — this is research material only."""


def script_prompt(
    topic: str,
    duration_minutes: int,
    research: str,
    host_name: str = "Alex",
    expert_names: list[str] | None = None,
) -> str:
    if expert_names is None:
        expert_names = ["Jordan"]

    total_words = 140 * duration_minutes
    main_words = int(total_words * 0.55)
    qa_words = int(total_words * 0.25)
    intro_words = 60
    outro_words = 40

    # ── Persona block ────────────────────────────────────────────────────────
    persona_lines = [
        f'- HOST = "{host_name}": curious, asks clarifying questions, '
        f'summarizes key points for the audience, occasional light humor',
    ]
    for i, name in enumerate(expert_names):
        if i == 0:
            persona_lines.append(
                f'- EXPERT_{i} = "{name}": knowledgeable, gives concrete examples, explains clearly, dry wit'
            )
        else:
            persona_lines.append(
                f'- EXPERT_{i} = "{name}": adds a different angle, builds on what the other expert says'
            )
    personas = "\n".join(persona_lines)

    # ── Valid speaker IDs ────────────────────────────────────────────────────
    expert_ids = [f"expert_{i}" for i in range(len(expert_names))]
    all_ids = ["host"] + expert_ids
    speaker_literal = " | ".join(f'"{s}"' for s in all_ids)

    # ── Q&A instructions ─────────────────────────────────────────────────────
    if len(expert_names) == 1:
        qa_note = (
            f'{host_name} transitions with "we got some great questions from listeners," '
            f'then asks 3–4 realistic learner questions. {expert_names[0]} answers each.'
        )
    else:
        expert_list = " and ".join(expert_names)
        qa_note = (
            f'{host_name} transitions with "we got some great questions from listeners," '
            f'then asks 3–4 realistic learner questions. {expert_list} take turns answering, '
            f'occasionally responding to each other.'
        )

    return f"""You are writing a podcast script. Output ONLY valid JSON — no markdown fences, no explanation.

PERSONAS:
{personas}

TOPIC: {topic}
TARGET DURATION: {duration_minutes} minutes (~{total_words} words total)

WORD BUDGET:
- intro: ~{intro_words} words
- main: ~{main_words} words
- qa: ~{qa_words} words ({qa_note})
- outro: ~{outro_words} words

RESEARCH MATERIAL:
{research}

RULES for each line:
- 1 to 3 sentences max per line
- Use contractions and casual speech
- NO stage directions, NO [laughs], NO emojis
- NO asterisks, underscores, hashtags, or markdown
- Spell out technical acronyms on first use (e.g. "Application Programming Interface, or API")
- Alternate speakers naturally — avoid 3+ consecutive lines from same speaker

OUTPUT FORMAT (strict JSON, no wrapper):
{{
  "lines": [
    {{"speaker": "host", "text": "...", "segment": "intro"}},
    {{"speaker": "expert_0", "text": "...", "segment": "intro"}},
    ...
  ]
}}

speaker must be one of: {speaker_literal}
segment must be "intro", "main", "qa", or "outro".
Write the complete script now."""
