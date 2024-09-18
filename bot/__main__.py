import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.redis import DefaultKeyBuilder, RedisStorage
from aiogram.enums import ParseMode
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from bot.config import settings, redis
from bot.handlers import (
    startup_router,
    add_account_router,
    start_account_router,
    utils_router,
)
from bot.menu_commands import set_default_commands
from bot.middlewares.db import DbSessionMiddleware


async def main():
    logging.basicConfig(
        format='[{asctime}] #{levelname:8} {filename}: '
               '{lineno} - {name} - {message}',
        style="{",
        level=logging.INFO,
    )

    bot = Bot(
        token=settings.TOKEN,
        default=DefaultBotProperties(
            parse_mode=ParseMode.HTML,
        )
    )
    async_engine = create_async_engine(settings.get_database_url)
    sessionmaker = async_sessionmaker(bind=async_engine, expire_on_commit=False)

    storage = RedisStorage(
        redis=redis,
        key_builder=DefaultKeyBuilder(with_destiny=True),
    )

    dp = Dispatcher(storage=storage)
    dp.update.middleware(middleware=DbSessionMiddleware(session_pool=sessionmaker))

    dp.include_routers(
        startup_router,
        add_account_router,
        start_account_router,
        utils_router,
    )

    await set_default_commands(bot)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    logger = logging.getLogger(__name__)

    try:
        asyncio.run(main())
    except (Exception, KeyboardInterrupt):
        logger.info("Bot stopped")