"""Generate text backups for bulk-deletion events."""

import datetime
import html

from config import settings
from services.catcher.paths import transcripts_dir


def generate_bulk_transcript(
    chat_id: int,
    message_ids: list[int],
    recovered_entries: list[dict[str, object]],
    sender_id: int,
    sender_name: str,
) -> tuple[str, str]:
    """Create a text backup for a bulk deletion event.

    Returns ``(file_path, alert_text)`` where ``file_path`` is the on-disk
    transcript ready to be uploaded to the admin chat and ``alert_text`` is the
    HTML caption that explains it.
    """
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    transcript_lines = [
        "=== АРХИВ УДАЛЕННОГО ДИАЛОГА ===",
        f"Собеседник: {sender_name} (ID: {sender_id})",
        f"Время массового удаления/очистки: {now_str}",
        f"Удалено сообщений: {len(recovered_entries)}",
        "=================================\n",
    ]

    recovered_entries.sort(key=lambda x: x.get("message_id", 0))

    for entry in recovered_entries:
        msg_time = entry.get("created_at", "unknown")
        msg_sender = sender_name if entry["sender_id"] != settings.ADMIN_ID else "Я (Владелец)"
        msg_text = entry["message_text"] or f"[{entry['media_type'] or 'Медиафайл'}]"
        transcript_lines.append(f"[{msg_time}] {msg_sender}: {msg_text}")

    transcript_content = "\n".join(transcript_lines)
    file_path = transcripts_dir() / f"transcript_deleted_{chat_id}.txt"
    file_path.write_text(transcript_content, encoding="utf-8")

    escaped_sender_name = html.escape(sender_name)
    alert_text = (
        f"⚠️ <b>Обнаружена очистка чата / Массовое удаление!</b>\n\n"
        f"👤 <a href=\"tg://user?id={sender_id}\">{escaped_sender_name}</a> "
        f"(<code>{sender_id}</code>) массово стёр <b>{len(message_ids)}</b> сообщений.\n\n"
        f"📝 Бот восстановил всю переписку и подготовил текстовый файл бэкапа:"
    )
    return str(file_path), alert_text
