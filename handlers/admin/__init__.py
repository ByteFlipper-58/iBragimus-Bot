from aiogram import F, Router

from config import settings
from handlers.admin import account, ai_settings, behavior, blacklist, menu, prompt

router = Router(name="admin")

# Defense in depth: restrict every admin interaction to the configured admin ID
# at the router level, so access does not rely solely on who can see the menu.
router.message.filter(F.from_user.id == settings.ADMIN_ID)
router.callback_query.filter(F.from_user.id == settings.ADMIN_ID)

router.include_router(menu.router)
router.include_router(prompt.router)
router.include_router(ai_settings.router)
router.include_router(behavior.router)
router.include_router(blacklist.router)
router.include_router(account.router)
