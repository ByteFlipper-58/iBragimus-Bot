"""Centralised filesystem paths used by media caching and transcripts."""

from pathlib import Path

MEDIA_CACHE_ROOT = Path("media_cache")
VIEW_ONCE_ROOT = MEDIA_CACHE_ROOT / "view_once"
TRANSCRIPTS_ROOT = MEDIA_CACHE_ROOT / "transcripts"


def chat_cache_dir(chat_id: int) -> Path:
    """Return the per-chat cache directory, creating it if needed."""
    path = MEDIA_CACHE_ROOT / str(chat_id)
    path.mkdir(parents=True, exist_ok=True)
    return path


def transcripts_dir() -> Path:
    """Return the transcript output directory, creating it if needed."""
    TRANSCRIPTS_ROOT.mkdir(parents=True, exist_ok=True)
    return TRANSCRIPTS_ROOT


def view_once_dir(sender_id: int | str | None) -> Path:
    """Return the per-sender view-once cache directory, creating it if needed."""
    sender_part = str(sender_id) if sender_id is not None else "unknown"
    path = VIEW_ONCE_ROOT / sender_part
    path.mkdir(parents=True, exist_ok=True)
    return path
