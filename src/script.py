"""Turn the day's article digest into a ~30 minute English radio-style script.

Uses the Claude API (Anthropic SDK) with adaptive thinking, streaming (the
script is long), and prompt caching on the stable system prompt.
"""
from __future__ import annotations

import os

import anthropic

# Default to the most capable model; override via CLAUDE_MODEL env var
# (e.g. claude-sonnet-4-6 / claude-haiku-4-5 to reduce cost).
MODEL = os.environ.get("CLAUDE_MODEL", "claude-opus-4-8")

# Frozen system prompt — kept byte-stable so prompt caching can hit. The
# volatile per-day content (the article digest, the date) goes in the user turn,
# never here. (Note: for a once-daily job the 5-min cache rarely survives between
# runs; the breakpoint costs nothing and helps if you ever re-run within minutes.)
SYSTEM_PROMPT = """\
You are the writer and host of a daily English-language tech news radio show \
called "The Morning Circuit". Your audience listens on their commute. Each \
episode covers the previous day's news in entertainment-tech, robotics, and IT.

Write a script meant to be READ ALOUD by a single host. Requirements:
- Natural spoken English, conversational and engaging — not a list of headlines.
- Structure: (1) a short warm cold-open + what's coming up, (2) themed segments \
grouping related stories with smooth transitions, (3) a brief wrap-up and sign-off.
- Select and prioritize the most significant stories; it's fine to skip minor ones \
and to spend more time on the important ones. Add light, sensible context and \
commentary, but do NOT invent facts, quotes, figures, or stories not present in \
the source material.
- This is a summary-and-commentary show: paraphrase, never read article text \
verbatim.
- Output ONLY the spoken words. No stage directions, speaker labels, headers, \
markdown, sound-effect cues, or bracketed notes — every character will be sent \
to a text-to-speech engine and spoken.
- Spell out things that must be read correctly (e.g. "twenty twenty-six", \
"a hundred and forty million dollars"). Avoid symbols, URLs, and emoji."""

USER_TEMPLATE = """\
Today is {date}. Here are the articles from the previous day, grouped loosely by \
category. Write today's episode of The Morning Circuit.

Target length: about {target_words} words (roughly 30 minutes at a natural \
speaking pace). Use the full length — go deep rather than rushing.

ARTICLES:
{digest}"""


def generate_script(digest: str, date_str: str, target_words: int = 4300) -> str:
    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env

    user_text = USER_TEMPLATE.format(
        date=date_str, target_words=target_words, digest=digest
    )

    # Stream because the output is long (~30 min ≈ several thousand words).
    with client.messages.stream(
        model=MODEL,
        max_tokens=32000,
        thinking={"type": "adaptive"},
        output_config={"effort": "high"},
        system=[
            {
                "type": "text",
                "text": SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[{"role": "user", "content": user_text}],
    ) as stream:
        final = stream.get_final_message()

    if final.stop_reason == "refusal":
        raise RuntimeError(f"Model refused: {final.stop_details}")

    text = "".join(b.text for b in final.content if b.type == "text").strip()
    u = final.usage
    print(
        f"Script generated: ~{len(text.split())} words "
        f"(in={u.input_tokens} out={u.output_tokens} "
        f"cache_read={u.cache_read_input_tokens})"
    )
    if not text:
        raise RuntimeError("Empty script returned")
    return text


if __name__ == "__main__":
    from datetime import datetime
    demo = "[1] (tech | Demo) Example headline\nA short summary of the story.\nURL: https://example.com\n"
    print(generate_script(demo, datetime.now().strftime("%A, %B %d, %Y"), target_words=200))
