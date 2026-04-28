"""Thin HTTP client for the Respeecher Ukrainian Real-Time TTS API.

API base : https://api.respeecher.com
Auth     : X-API-Key header
Voices   : GET  /v1/public/tts/ua-rt/voices
Synthesize: POST /v1/public/tts/ua-rt/tts/bytes  → raw audio bytes
"""

import requests
from typing import Optional

BASE_URL = "https://api.respeecher.com"
_LANG = "ua-rt"
_HTTP_TIMEOUT = (10, 60)

AUDIO_EXTENSIONS = ("mp3", "wav", "ogg", "flac")


def _session(api_key: str) -> requests.Session:
    s = requests.Session()
    s.headers.update({"X-API-Key": api_key})
    return s


def list_voices(api_key: str) -> list[dict]:
    """Return list of voice dicts with 'id' and 'full_name'."""
    r = _session(api_key).get(
        f"{BASE_URL}/v1/public/tts/{_LANG}/voices",
        timeout=_HTTP_TIMEOUT,
    )
    r.raise_for_status()
    return r.json()


def synthesize(api_key: str, text: str, voice_id: str) -> tuple[bytes, str]:
    """Synthesize *text* with *voice_id* and return *(audio_bytes, extension)*."""
    r = _session(api_key).post(
        f"{BASE_URL}/v1/public/tts/{_LANG}/tts/bytes",
        json={"transcript": text, "voice": {"id": voice_id}},
        headers={"Content-Type": "application/json"},
        timeout=(10, 120),
    )
    r.raise_for_status()
    content_type = r.headers.get("content-type", "")
    if "wav" in content_type:
        ext = "wav"
    elif "mp3" in content_type or "mpeg" in content_type:
        ext = "mp3"
    elif "ogg" in content_type:
        ext = "ogg"
    elif "flac" in content_type:
        ext = "flac"
    else:
        ext = "wav"
    return r.content, ext
