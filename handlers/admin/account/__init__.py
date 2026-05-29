"""Admin screens for the connected Telegram account.

The package replaces the previous monolithic ``handlers/admin/account.py`` and
splits responsibilities by login flow:

* ``status``      — show the current Telegram account state.
* ``qr_login``    — QR-based login.
* ``phone_login`` — manual phone-number login.
* ``twofa``       — 2FA password handler shared by both flows.
* ``reset``       — drop the local session and recreate the client.
* ``errors``      — human-friendly Telethon error formatting.
* ``qr``          — PNG QR-code rendering.
* ``utils``       — small input helpers (normalisation, message cleanup).

The exported ``router`` aggregates every sub-router so callers continue to
include a single router from the admin package.
"""

from aiogram import Router

from handlers.admin.account import phone_login, qr_login, reset, status, twofa

router = Router(name="admin_account")
router.include_router(status.router)
router.include_router(qr_login.router)
router.include_router(phone_login.router)
router.include_router(twofa.router)
router.include_router(reset.router)

__all__ = ("router",)
