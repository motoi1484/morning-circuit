"""Daily pipeline: collect -> script -> TTS -> save episode -> rebuild feed.

Entry point for the GitHub Actions cron job.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from pathlib import Path

from collect import JST, collect, to_digest
from feed import EPISODES, build_feed
from script import generate_script
from tts import synthesize


def _prune(keep: int) -> None:
    """Keep only the newest `keep` episodes (mp3 + json + txt)."""
    mp3s = sorted(EPISODES.glob("*.mp3"), reverse=True)
    for old in mp3s[keep:]:
        for ext in (".mp3", ".json", ".txt"):
            old.with_suffix(ext).unlink(missing_ok=True)
        print(f"Pruned {old.stem}")


def run() -> None:
    now_jst = datetime.now(JST)
    # The episode covers the previous JST day.
    episode_date = (now_jst - timedelta(days=1)).date()
    slug = episode_date.isoformat()  # YYYY-MM-DD
    date_str = episode_date.strftime("%A, %B %d, %Y")

    target_words = int(os.environ.get("TARGET_WORDS", "4300"))
    keep = int(os.environ.get("KEEP_EPISODES", "14"))

    # 1. Collect
    articles = collect(now_jst)
    if not articles:
        print("No articles found for the window — skipping today.")
        return

    # 2. Script
    digest = to_digest(articles)
    script_text = generate_script(digest, date_str, target_words)

    # 3. TTS
    EPISODES.mkdir(parents=True, exist_ok=True)
    mp3_path = EPISODES / f"{slug}.mp3"
    synthesize(script_text, str(mp3_path))

    # 4. Metadata sidecars
    (EPISODES / f"{slug}.txt").write_text(script_text, encoding="utf-8")
    words = len(script_text.split())
    minutes, seconds = divmod(round(words / 150 * 60), 60)  # ~150 wpm
    headlines = "; ".join(a.title for a in articles[:5])
    meta = {
        "title": f"The Morning Circuit — {date_str}",
        "description": f"Top stories: {headlines}.",
        "pub_date": format_datetime(
            datetime.combine(episode_date, datetime.min.time(), tzinfo=JST).replace(
                hour=6
            ).astimezone(timezone.utc)
        ),
        "size": mp3_path.stat().st_size,
        "duration": f"{minutes:02d}:{seconds:02d}",
    }
    (EPISODES / f"{slug}.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # 5. Prune + rebuild feed
    _prune(keep)
    build_feed()
    print(f"Done: episode {slug} ({meta['duration']}).")


if __name__ == "__main__":
    run()
