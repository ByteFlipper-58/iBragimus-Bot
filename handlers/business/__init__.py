from aiogram import Router

from handlers.business import connections, deletions, edits, messages

router = Router(name="business")
router.include_router(connections.router)
router.include_router(messages.router)
router.include_router(edits.router)
router.include_router(deletions.router)
