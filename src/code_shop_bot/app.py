from aiogram import Bot, Dispatcher

from .config import load_settings
from .database import Database
from .handlers_admin import admin_router
from .handlers_user import user_router
from .middlewares import TouchUserMiddleware


async def run() -> None:
    settings = load_settings()
    settings.database_path.parent.mkdir(parents=True, exist_ok=True)

    database = Database(settings.database_path)
    await database.connect()
    await database.setup()
    await database.import_legacy_json(settings.legacy_json_path)

    bot = Bot(settings.bot_token)
    dispatcher = Dispatcher(settings=settings, database=database)
    dispatcher.message.middleware(TouchUserMiddleware())
    dispatcher.callback_query.middleware(TouchUserMiddleware())
    dispatcher.include_router(admin_router)
    dispatcher.include_router(user_router)

    print(f"{settings.store_name} bot started.")

    try:
        await dispatcher.start_polling(bot, allowed_updates=dispatcher.resolve_used_update_types())
    finally:
        await bot.session.close()
        await database.close()
