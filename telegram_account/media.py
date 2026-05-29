"""Small Telethon helpers for inspecting and naming incoming media."""

from telethon import utils
from telethon.tl.types import (
    Document,
    DocumentAttributeAudio,
    DocumentAttributeVideo,
    MessageMediaDocument,
    MessageMediaPhoto,
)


def is_view_once_media(media) -> bool:
    """Return whether a Telegram media object is protected by a TTL."""
    return getattr(media, "ttl_seconds", None) is not None


def format_ttl(ttl: int | None) -> str:
    """Format a Telegram media TTL for Saved Messages captions."""
    if ttl is None or ttl <= 0 or ttl >= 2_147_483_647:
        return "после одного просмотра"
    if ttl < 60:
        return f"{ttl} сек."
    minutes, seconds = divmod(ttl, 60)
    if minutes < 60:
        return f"{minutes} мин. {seconds} сек."
    hours, minutes = divmod(minutes, 60)
    return f"{hours} ч. {minutes} мин."


def _has_document_attribute(document: Document, attribute_type: type) -> bool:
    """Check whether a Telegram document carries a specific media attribute."""
    return any(
        isinstance(attribute, attribute_type)
        for attribute in (getattr(document, "attributes", None) or [])
    )


def _document_kind_and_extension(document: Document) -> tuple[str, str]:
    """Detect media kind and file extension for a Telegram document."""
    mime_type = (getattr(document, "mime_type", "") or "").lower()
    extension = utils.get_extension(document)

    if _has_document_attribute(document, DocumentAttributeVideo) or mime_type.startswith("video/"):
        return "video", extension or ".mp4"
    if mime_type.startswith("image/"):
        return "image", extension or ".jpg"
    if _has_document_attribute(document, DocumentAttributeAudio) or mime_type.startswith("audio/"):
        return "audio", extension or ".ogg"

    return "media", extension


def media_download_target(media) -> tuple[object, str, str]:
    """Return the exact Telegram object that should be downloaded.

    Returns ``(target, kind, extension)`` where ``target`` is what should be
    passed to ``client.download_media``, ``kind`` is a short string used in
    captions/filenames, and ``extension`` is the suggested file extension
    (including the leading dot, may be empty).
    """
    attached_video = getattr(media, "video", None)
    if isinstance(attached_video, Document):
        _, extension = _document_kind_and_extension(attached_video)
        return attached_video, "video", extension or ".mp4"

    if isinstance(media, MessageMediaDocument) and isinstance(media.document, Document):
        media_kind, extension = _document_kind_and_extension(media.document)
        if getattr(media, "video", False):
            return media.document, "video", extension or ".mp4"
        return media.document, media_kind, extension

    if isinstance(media, MessageMediaPhoto):
        return media, "photo", ".jpg"

    return media, "media", ""


def sender_display_name(sender) -> str:
    """Format the sender name used in logs and Saved Messages captions."""
    sender_name = getattr(sender, "first_name", None) or "Неизвестный"
    if getattr(sender, "last_name", None):
        sender_name += f" {sender.last_name}"

    sender_username = getattr(sender, "username", "")
    return sender_name + (f" (@{sender_username})" if sender_username else "")
