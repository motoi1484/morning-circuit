"""Local test runner: collect -> script -> TTS, saving outputs to samples/.

Does NOT touch docs/episodes/ or the feed — purely for trying things out.

Usage:
    PYTHONPATH=src python src/preview.py            # ~400-word short preview
    PYTHONPATH=src python src/preview.py 4300        # full ~30 min length

Output files land in samples/ as preview_<timestamp>.{txt,mp3}.
"""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

from collect import JST, collect, to_digest
from script import generate_script
from tts import synthesize

SAMPLES = Path(__file__).resolve().parent.parent / "samples"


def main() -> None:
    target_words = int(sys.argv[1]) if len(sys.argv) > 1 else 400

    SAMPLES.mkdir(exist_ok=True)
    stamp = datetime.now(JST).strftime("%Y%m%d-%H%M%S")
    txt_path = SAMPLES / f"preview_{stamp}.txt"
    mp3_path = SAMPLES / f"preview_{stamp}.mp3"

    now_jst = datetime.now(JST)
    date_str = now_jst.strftime("%A, %B %d, %Y")

    articles = collect(now_jst)
    if not articles:
        print("No articles found — nothing to preview.")
        return

    text = generate_script(to_digest(articles), date_str, target_words)
    txt_path.write_text(text, encoding="utf-8")
    synthesize(text, str(mp3_path))

    print(f"\nSaved:\n  {txt_path}\n  {mp3_path}")


if __name__ == "__main__":
    main()
