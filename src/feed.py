"""Generate a podcast RSS feed (docs/feed.xml) from the committed episodes.

Each episode is a pair under docs/episodes/:
  <YYYY-MM-DD>.mp3   — the audio
  <YYYY-MM-DD>.json  — metadata {title, description, pub_date, size, duration}
"""
from __future__ import annotations

import json
import os
from email.utils import format_datetime
from pathlib import Path
from xml.sax.saxutils import escape

DOCS = Path(__file__).resolve().parent.parent / "docs"
EPISODES = DOCS / "episodes"

PODCAST_TITLE = "The Morning Circuit"
PODCAST_DESCRIPTION = (
    "A daily English-language briefing on entertainment-tech, robotics, and IT — "
    "the previous day's news, auto-generated for your commute."
)
PODCAST_AUTHOR = "The Morning Circuit"
PODCAST_LANGUAGE = "en-us"


def _base_url() -> str:
    base = os.environ.get("PODCAST_BASE_URL", "").strip()
    if not base:
        raise RuntimeError("PODCAST_BASE_URL is not set")
    return base.rstrip("/") + "/"


def _load_episodes() -> list[dict]:
    eps = []
    for meta_path in sorted(EPISODES.glob("*.json"), reverse=True):
        mp3 = meta_path.with_suffix(".mp3")
        if not mp3.exists():
            continue
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        meta["_mp3_name"] = mp3.name
        eps.append(meta)
    return eps


def _item_xml(ep: dict, base: str) -> str:
    url = f"{base}episodes/{ep['_mp3_name']}"
    return f"""    <item>
      <title>{escape(ep['title'])}</title>
      <description>{escape(ep['description'])}</description>
      <pubDate>{escape(ep['pub_date'])}</pubDate>
      <enclosure url="{escape(url)}" length="{ep['size']}" type="audio/mpeg"/>
      <guid isPermaLink="true">{escape(url)}</guid>
      <itunes:duration>{escape(str(ep.get('duration', '')))}</itunes:duration>
    </item>"""


def build_feed() -> str:
    base = _base_url()
    eps = _load_episodes()
    now = format_datetime(__import__("datetime").datetime.now(
        __import__("datetime").timezone.utc))
    items = "\n".join(_item_xml(ep, base) for ep in eps)

    feed = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd">
  <channel>
    <title>{escape(PODCAST_TITLE)}</title>
    <link>{escape(base)}</link>
    <language>{PODCAST_LANGUAGE}</language>
    <description>{escape(PODCAST_DESCRIPTION)}</description>
    <itunes:author>{escape(PODCAST_AUTHOR)}</itunes:author>
    <itunes:explicit>false</itunes:explicit>
    <lastBuildDate>{now}</lastBuildDate>
{items}
  </channel>
</rss>
"""
    out = DOCS / "feed.xml"
    out.write_text(feed, encoding="utf-8")
    print(f"Wrote {out} with {len(eps)} episodes")
    return str(out)


if __name__ == "__main__":
    build_feed()
