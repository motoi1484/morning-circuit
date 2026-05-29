"""Collect yesterday's articles from the configured RSS feeds.

Run at ~05:00 JST and gather everything published during the *previous* JST
calendar day.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

import feedparser
import yaml

JST = timezone(timedelta(hours=9))
CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "sources.yaml"


@dataclass
class Article:
    source: str
    category: str
    title: str
    summary: str
    link: str
    published_iso: str  # UTC ISO-8601


def _yesterday_window_utc(now_jst: datetime) -> tuple[datetime, datetime]:
    """Return [start, end) in UTC covering the previous JST calendar day."""
    today_start_jst = now_jst.replace(hour=0, minute=0, second=0, microsecond=0)
    start_jst = today_start_jst - timedelta(days=1)
    return start_jst.astimezone(timezone.utc), today_start_jst.astimezone(timezone.utc)


def _entry_published_utc(entry) -> datetime | None:
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if not parsed:
        return None
    # feedparser normalizes *_parsed to a UTC struct_time.
    return datetime(*parsed[:6], tzinfo=timezone.utc)


def _clean(text: str, limit: int = 600) -> str:
    import html
    import re
    text = re.sub(r"<[^>]+>", "", text or "")
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit]


def load_config() -> dict:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def collect(now_jst: datetime | None = None) -> list[Article]:
    cfg = load_config()
    now_jst = now_jst or datetime.now(JST)
    start_utc, end_utc = _yesterday_window_utc(now_jst)

    articles: list[Article] = []
    seen_links: set[str] = set()

    for feed in cfg["feeds"]:
        parsed = feedparser.parse(feed["url"])
        if parsed.bozo:
            print(f"  [warn] {feed['name']}: {parsed.bozo_exception}")
        for entry in parsed.entries:
            pub = _entry_published_utc(entry)
            if pub is None or not (start_utc <= pub < end_utc):
                continue
            link = entry.get("link", "")
            if link in seen_links:
                continue
            seen_links.add(link)
            articles.append(
                Article(
                    source=feed["name"],
                    category=feed.get("category", "general"),
                    title=_clean(entry.get("title", ""), 300),
                    summary=_clean(entry.get("summary", "")),
                    link=link,
                    published_iso=pub.isoformat(),
                )
            )

    articles.sort(key=lambda a: a.published_iso, reverse=True)
    max_n = cfg.get("max_articles", 40)
    selected = articles[:max_n]
    print(
        f"Collected {len(selected)} articles "
        f"(window {start_utc.isoformat()} .. {end_utc.isoformat()})"
    )
    return selected


def to_digest(articles: list[Article]) -> str:
    """Render the articles into a compact text block for the script prompt."""
    lines = []
    for i, a in enumerate(articles, 1):
        lines.append(
            f"[{i}] ({a.category} | {a.source}) {a.title}\n{a.summary}\nURL: {a.link}\n"
        )
    return "\n".join(lines)


if __name__ == "__main__":
    arts = collect()
    print(to_digest(arts)[:2000])
