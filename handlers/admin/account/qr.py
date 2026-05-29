"""Render Telegram login URLs as PNG QR codes."""

import io

import segno


def build_qr_png(payload: str) -> bytes:
    """Render a Telegram login URL as PNG bytes for the admin chat."""
    buffer = io.BytesIO()
    qr = segno.make(payload, error="m")
    qr.save(buffer, kind="png", scale=8, border=4, dark="black", light="white")
    return buffer.getvalue()
