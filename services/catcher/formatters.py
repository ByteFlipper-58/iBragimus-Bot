"""HTML formatters for admin edit/delete alerts."""

import html


def format_edit_timeline(
    sender_id: int,
    sender_name: str,
    old_text: str,
    new_text: str,
    history: list[dict[str, object]],
) -> str:
    """Build an HTML timeline for an edited message."""
    escaped_sender_name = html.escape(sender_name or "Неизвестный")

    if not history:
        escaped_old_text = html.escape(old_text)
        escaped_new_text = html.escape(new_text)
        return (
            f"✏️ <a href=\"tg://user?id={sender_id}\">{escaped_sender_name}</a> "
            f"(<code>{sender_id}</code>) отредактировал сообщение:\n\n"
            f"<blockquote>{escaped_old_text}</blockquote>"
            f"⇩⇩⇩\n"
            f"<blockquote>{escaped_new_text}</blockquote>"
        )

    versions = [history[0]["old_text"]]
    for entry in history:
        versions.append(entry["new_text"])

    parts = [
        f"✏️ <a href=\"tg://user?id={sender_id}\">{escaped_sender_name}</a> "
        f"(<code>{sender_id}</code>) отредактировал сообщение (правка №{len(history)}):\n"
    ]

    for idx, text in enumerate(versions):
        escaped_ver = html.escape(text)
        if idx == 0:
            parts.append(f"<b>[1] Оригинал:</b>\n<blockquote>{escaped_ver}</blockquote>")
        elif idx == len(versions) - 1:
            parts.append(
                f"⇩⇩⇩\n<b>[{idx+1}] Итоговый текст:</b>\n<blockquote>{escaped_ver}</blockquote>"
            )
        else:
            rev_time = history[idx - 1]["edited_at"][11:19]
            parts.append(
                f"⇩⇩⇩\n<b>[{idx+1}] Редакция от {rev_time}:</b>\n<blockquote>{escaped_ver}</blockquote>"
            )

    return "\n".join(parts)


def format_delete_alert(original: dict[str, object]) -> tuple[str, str | None, str | None]:
    """Build the delete alert text and return cached media info."""
    sender_id = original["sender_id"]
    sender_name = original["sender_name"] or "Неизвестный"
    message_text = original["message_text"]
    media_file_path = original.get("media_file_path")
    media_type = original.get("media_type")

    escaped_sender_name = html.escape(sender_name)
    escaped_message_text = html.escape(message_text or "")

    if not escaped_message_text and media_type:
        escaped_message_text = f"[{media_type.upper()} ФАЙЛ]"

    alert_text = (
        f"🗑 <b>Это сообщение было удалено</b>\n\n"
        f"<a href=\"tg://user?id={sender_id}\">{escaped_sender_name}</a> "
        f"(<code>{sender_id}</code>)\n"
        f"<blockquote>{escaped_message_text}</blockquote>"
    )
    return alert_text, media_file_path, media_type
