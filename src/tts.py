"""Synthesize the narration script to an MP3 with Google Cloud Text-to-Speech.

Google TTS limits a single request to 5000 bytes, so the script is split into
chunks on sentence boundaries and the resulting MP3 segments are concatenated.
MP3 frames concatenate cleanly for sequential playback.
"""
from __future__ import annotations

import os
import re

from google.cloud import texttospeech

# Stay safely under the 5000-byte API limit (bytes, not chars).
MAX_CHUNK_BYTES = 4000


def _split_into_chunks(text: str, max_bytes: int = MAX_CHUNK_BYTES) -> list[str]:
    # Split on sentence-ish boundaries, then greedily pack into chunks.
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    chunks: list[str] = []
    current = ""
    for sentence in sentences:
        candidate = f"{current} {sentence}".strip()
        if len(candidate.encode("utf-8")) > max_bytes and current:
            chunks.append(current)
            current = sentence
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks


def synthesize(text: str, out_path: str) -> str:
    client = texttospeech.TextToSpeechClient()

    voice_name = os.environ.get("TTS_VOICE", "en-US-Neural2-D")
    language_code = "-".join(voice_name.split("-")[:2])  # e.g. "en-US"
    speaking_rate = float(os.environ.get("TTS_RATE", "1.0"))

    voice = texttospeech.VoiceSelectionParams(
        language_code=language_code, name=voice_name
    )
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3,
        speaking_rate=speaking_rate,
    )

    chunks = _split_into_chunks(text)
    print(f"Synthesizing {len(chunks)} chunks with voice {voice_name}...")

    with open(out_path, "wb") as out:
        for i, chunk in enumerate(chunks, 1):
            resp = client.synthesize_speech(
                input=texttospeech.SynthesisInput(text=chunk),
                voice=voice,
                audio_config=audio_config,
            )
            out.write(resp.audio_content)
            if i % 5 == 0 or i == len(chunks):
                print(f"  {i}/{len(chunks)} chunks done")

    size = os.path.getsize(out_path)
    print(f"Wrote {out_path} ({size / 1024 / 1024:.1f} MB)")
    return out_path


if __name__ == "__main__":
    synthesize("Hello and welcome to the Morning Circuit. This is a test.", "/tmp/test.mp3")
