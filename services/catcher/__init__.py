"""Edit/delete recovery utilities used by Business handlers.

The package replaces the previous ``services/catcher_service.py`` static class.
Concerns are split by responsibility:

* ``media_downloader`` — downloads attachments to the local cache.
* ``formatters``       — HTML formatting for admin alerts.
* ``transcript``       — bulk-deletion text backup file generation.

A backwards-compatible ``CatcherService`` shim is exported so existing imports
keep working while call sites are migrated.
"""

from services.catcher.formatters import format_delete_alert, format_edit_timeline
from services.catcher.media_downloader import download_media_file
from services.catcher.transcript import generate_bulk_transcript


class CatcherService:
    """Backwards-compatible facade preserving the previous static API."""

    download_media_file = staticmethod(download_media_file)
    format_edit_timeline = staticmethod(format_edit_timeline)
    format_delete_alert = staticmethod(format_delete_alert)
    generate_bulk_transcript = staticmethod(generate_bulk_transcript)


__all__ = (
    "CatcherService",
    "download_media_file",
    "format_edit_timeline",
    "format_delete_alert",
    "generate_bulk_transcript",
)
