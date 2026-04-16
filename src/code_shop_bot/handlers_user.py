from aiogram import Bot, F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, Message

from .config import Settings
from .database import Database
from .keyboards import Buttons
from .services import (
    create_order,
    mark_paid,
    send_help,
    send_main_menu,
    show_catalog,
    show_product,
    show_user_orders,
)


user_router = Router(name="user")


@user_router.message(CommandStart())
async def start(message: Message, settings: Settings) -> None:
    await send_main_menu(
        message,
        settings,
        f"Вітаю у {settings.store_name}.\n\nОбери товар з каталогу, створи замовлення, оплати його і отримай код прямо тут.",
    )


@user_router.message(Command("catalog"))
@user_router.message(F.text == Buttons.catalog)
async def catalog(message: Message, database: Database, settings: Settings) -> None:
    await show_catalog(message, database, settings)


@user_router.message(Command("orders"))
@user_router.message(F.text == Buttons.orders)
async def orders(message: Message, database: Database, settings: Settings) -> None:
    await show_user_orders(message, database, settings)


@user_router.message(Command("help"))
@user_router.message(F.text == Buttons.help)
async def help_message(message: Message, settings: Settings) -> None:
    await send_help(message, settings)


@user_router.message(Command("id"))
async def my_id(message: Message) -> None:
    if not message.from_user:
        await message.answer("Не бачу твій Telegram ID.")
        return

    await message.answer(f"Твій Telegram ID: {message.from_user.id}")


@user_router.message(F.text == Buttons.main_menu)
async def main_menu(message: Message, settings: Settings) -> None:
    await send_main_menu(message, settings)


@user_router.message(F.text)
async def product_or_unknown(message: Message, database: Database, settings: Settings) -> None:
    product = await database.find_product_by_button(message.text or "")
    if product:
        await show_product(message, database, product["id"])
        return

    await message.answer("Не впізнав команду. Натисни /start або напиши: Головне меню")


@user_router.callback_query(F.data == "catalog")
async def catalog_callback(callback: CallbackQuery, database: Database, settings: Settings) -> None:
    await callback.answer()
    if isinstance(callback.message, Message):
        await show_catalog(callback.message, database, settings)


@user_router.callback_query(F.data == "orders")
async def orders_callback(callback: CallbackQuery, database: Database, settings: Settings) -> None:
    await callback.answer()
    if isinstance(callback.message, Message):
        await show_user_orders(callback.message, database, settings)


@user_router.callback_query(F.data == "help")
async def help_callback(callback: CallbackQuery, settings: Settings) -> None:
    await callback.answer()
    if isinstance(callback.message, Message):
        await send_help(callback.message, settings)


@user_router.callback_query(F.data == "main_menu")
async def main_menu_callback(callback: CallbackQuery, settings: Settings) -> None:
    await callback.answer()
    if isinstance(callback.message, Message):
        await send_main_menu(callback.message, settings)


@user_router.callback_query(F.data.startswith("product:"))
async def product_callback(callback: CallbackQuery, database: Database) -> None:
    await callback.answer()
    if isinstance(callback.message, Message) and callback.data:
        await show_product(callback.message, database, callback.data.removeprefix("product:"))


@user_router.callback_query(F.data.startswith("buy:"))
async def buy_callback(callback: CallbackQuery, bot: Bot, database: Database, settings: Settings) -> None:
    await callback.answer()
    if isinstance(callback.message, Message) and callback.data:
        await create_order(callback.message, bot, database, settings, callback.data.removeprefix("buy:"))


@user_router.callback_query(F.data.startswith("paid:"))
async def paid_callback(callback: CallbackQuery, bot: Bot, database: Database, settings: Settings) -> None:
    await callback.answer()
    if isinstance(callback.message, Message) and callback.data:
        await mark_paid(callback.message, bot, database, settings, callback.data.removeprefix("paid:"))
