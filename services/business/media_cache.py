"""Cache attachments arriving in Business messages onto the local filesystem."""

from typing import Awaitable, Callable

from aiogram import Bot
from aiogram.types import Message

from services.catcher.media_downloader import download_media_file

# Each entry returns ``(file_id, ext, media_type)`` for a given message, or
# ``None`` when the message does not carry that kind of attachment.
_DEFAULT_EXTENSIONS = {
    "photo": "jpg",
    "video": "mp4",
    "voice": "ogg",
    "document": "doc",
    "audio": "mp3",
    "animation": "mp4",
}


def _photo(message: Message) -> tuple[str, str, str] | None:
    if not message.photo:
        return None
    return message.photo[-1].file_id, _DEFAULT_EXTENSIONS["photo"], "photo"


def _video(message: Message) -> tuple[str, str, str] | None:
    if not message.video:
        return None
    return message.video.file_id, _DEFAULT_EXTENSIONS["video"], "video"


def _voice(message: Message) -> tuple[str, str, str] | None:
    if not message.voice:
        return None
    return message.voice.file_id, _DEFAULT_EXTENSIONS["voice"], "voice"


def _document(message: Message) -> tuple[str, str, str] | None:
    if not message.document:
        return None
    name = message.document.file_name or ""
    ext = name.rsplit(".", 1)[-1] if "." in name else _DEFAULT_EXTENSIONS["document"]
    return message.document.file_id, ext, "document"


def _audio(message: Message) -> tuple[str, str, str] | None:
    if not message.audio:
        return None
    return message.audio.file_id, _DEFAULT_EXTENSIONS["audio"], "audio"


def _sticker(message: Message) -> tuple[str, str, str] | None:
    sticker = message.sticker
    if not sticker:
        return None
    if sticker.is_animated:
        ext = "tgs"
    elif sticker.is_video:
        ext = "webm"
    else:
        ext = "webp"
    return sticker.file_id, ext, "sticker"


def _animation(message: Message) -> tuple[str, str, str] | None:
    if not message.animation:
        return None
    return message.animation.file_id, _DEFAULT_EXTENSIONS["animation"], "animation"


# Order matters: photos and videos come before generic documents so albums and
# captioned media are detected correctly.
_RESOLVERS: tuple[Callable[[Message], tuple[str, str, str] | None], ...] = (
    _photo,
    _video,
    _voice,
    _document,
    _audio,
    _sticker,
    _animation,
)


async def cache_message_media(
    message: Message,
    bot: Bot,
    *,
    download: Callable[..., Awaitable[str | None]] = download_media_file,
) -> tuple[str | None, str | None]:
    """Detect and cache the first supported attachment on ``message``.

    Returns ``(file_path, media_type)`` or ``(None, None)`` if the message has
    no supported media. ``download`` is injectable to make tests independent of
    the Telegram Bot API.
    """
    chat_id = message.chat.id
    message_id = message.message_id

    for resolver in _RESOLVERS:
        match = resolver(message)
        if match is None:
            continue
        file_id, ext, media_type = match
        path = await download(bot, file_id, chat_id, message_id, media_type, ext)
        return path, media_type

    return None, None
