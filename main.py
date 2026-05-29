import asyncio
import logging
import sys

if sys.platform.startswith('win'):
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8')

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from config import settings
from database.db import DatabaseManager
from database.repository import BotRepository
from middlewares.db_middleware import DatabaseMiddleware
from handlers import admin, business
from telegram_account import get_client, get_existing_client

logging.basicConfig(
    level=logging.getLevelName(settings.LOG_LEVEL),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


async def on_startup(bot: Bot, db_manager: DatabaseManager) -> None:
    """Initialize storage and Telegram bot commands before polling starts."""
    logger.info("Starting iBragimusBot...")
    await db_manager.initialize_db()
    
    try:
        from aiogram.types import BotCommand
        await bot.set_my_commands([
            BotCommand(command="menu", description="Открыть меню iBragimusBot"),
            BotCommand(command="start", description="Запустить iBragimusBot")
        ])
        logger.info("Bot commands successfully registered in Telegram.")
    except Exception as e:
        logger.warning("Failed to set bot commands: %s", e)


async def on_shutdown(_dispatcher: Dispatcher, db_manager: DatabaseManager) -> None:
    """Run shutdown hooks after aiogram stops polling."""
    logger.info("Shutting down bot polling...")
    await db_manager.close()
    logger.info("Bot shutdown completed successfully.")


async def main() -> None:
    """Start the Telegram Business bot and connected account client."""
    logger.info("Initializing bot components...")
    
    db_manager = DatabaseManager()
    repository = BotRepository(db_manager)

    try:
        bot = Bot(
            token=settings.BOT_TOKEN,
            default=DefaultBotProperties(parse_mode="HTML")
        )
    except Exception as e:
        logger.critical("Failed to initialize Bot with given token: %s", e)
        logger.critical("Please make sure BOT_TOKEN is set to a valid token in the .env file.")
        sys.exit(1)

    dp = Dispatcher()

    db_middleware = DatabaseMiddleware(repository)
    
    dp.message.middleware(db_middleware)
    dp.callback_query.middleware(db_middleware)
    dp.business_message.middleware(db_middleware)
    dp.edited_business_message.middleware(db_middleware)
    dp.deleted_business_messages.middleware(db_middleware)
    dp.business_connection.middleware(db_middleware)
    
    dp.include_router(admin.router)
    dp.include_router(business.router)

    account_client = get_client()
    logger.info("Connecting Telegram account client...")
    await account_client.connect()
    if await account_client.is_user_authorized():
        logger.info("Telegram account client is authorized and active.")
    else:
        logger.info("Telegram account client is not authorized yet. Finish login in the admin chat.")

    async def _on_startup() -> None:
        await on_startup(bot, db_manager)

    async def _on_shutdown() -> None:
        await on_shutdown(dp, db_manager)
        current_client = get_existing_client()
        if current_client and current_client.is_connected():
            logger.info("Disconnecting Telegram account client...")
            await current_client.disconnect()
            logger.info("Telegram account client disconnected successfully.")
        
    dp.startup.register(_on_startup)
    dp.shutdown.register(_on_shutdown)

    logger.info("Starting bot polling...")
    try:
        allowed_updates = [
            "message", 
            "callback_query", 
            "business_connection", 
            "business_message",
            "edited_business_message",
            "deleted_business_messages"
        ]
        await bot.delete_webhook(drop_pending_updates=True)
        
        logger.info("Launching aiogram bot polling...")
        await dp.start_polling(bot, allowed_updates=allowed_updates)
    except Exception as e:
        logger.critical("Critical error during bot polling: %s", e, exc_info=True)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot process interrupted by user. Exiting...")
