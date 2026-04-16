from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from .config import Settings
from .database import Database
from .keyboards import Buttons
from .services import (
    add_code,
    add_codes,
    add_product,
    add_products,
    cancel_order,
    confirm_order,
    send_admin_help,
    show_admin,
    show_admin_orders,
    show_admin_products,
    show_stock,
)


admin_router = Router(name="admin")


def is_admin(message: Message, settings: Settings) -> bool:
    return bool(message.from_user and message.from_user.id in settings.admin_ids)


@admin_router.message(Command("admin"))
@admin_router.message(F.text == Buttons.admin)
async def admin(message: Message, database: Database, settings: Settings) -> None:
    await show_admin(message, database, settings)


@admin_router.message(Command("stock"))
@admin_router.message(F.text == Buttons.admin_stock)
async def stock(message: Message, database: Database, settings: Settings) -> None:
    await show_stock(message, database, settings)


@admin_router.message(F.text == Buttons.admin_orders)
async def admin_orders(message: Message, database: Database, settings: Settings) -> None:
    await show_admin_orders(message, database, settings)


@admin_router.message(F.text == Buttons.admin_products)
async def admin_products(message: Message, database: Database, settings: Settings) -> None:
    await show_admin_products(message, database, settings)


@admin_router.message(F.text == Buttons.admin_help)
async def admin_help(message: Message, settings: Settings) -> None:
    await send_admin_help(message, settings)


@admin_router.message(F.text.startswith("/addproduct "))
async def add_product_message(message: Message, database: Database, settings: Settings) -> None:
    if not is_admin(message, settings):
        await message.answer("Ця команда доступна тільки адміну.")
        return
    await add_product(message, database)


@admin_router.message(F.text.startswith("/addproducts"))
async def add_products_message(message: Message, database: Database, settings: Settings) -> None:
    if not is_admin(message, settings):
        await message.answer("Ця команда доступна тільки адміну.")
        return
    await add_products(message, database)


@admin_router.message(F.text.startswith("/addcode "))
async def add_code_message(message: Message, database: Database, settings: Settings) -> None:
    if not is_admin(message, settings):
        await message.answer("Ця команда доступна тільки адміну.")
        return
    await add_code(message, database)


@admin_router.message(F.text.startswith("/addcodes"))
async def add_codes_message(message: Message, database: Database, settings: Settings) -> None:
    if not is_admin(message, settings):
        await message.answer("Ця команда доступна тільки адміну.")
        return
    await add_codes(message, database)


@admin_router.message(F.text.startswith("/confirm "))
async def confirm_message(message: Message, bot: Bot, database: Database, settings: Settings) -> None:
    if not is_admin(message, settings):
        await message.answer("Ця команда доступна тільки адміну.")
        return
    await confirm_order(message, bot, database, (message.text or "").replace("/confirm", "", 1).strip())


@admin_router.message(F.text.startswith("/cancel "))
async def cancel_message(message: Message, bot: Bot, database: Database, settings: Settings) -> None:
    if not is_admin(message, settings):
        await message.answer("Ця команда доступна тільки адміну.")
        return
    await cancel_order(message, bot, database, (message.text or "").replace("/cancel", "", 1).strip())


@admin_router.callback_query(F.data == "admin")
async def admin_callback(callback: CallbackQuery, database: Database, settings: Settings) -> None:
    await callback.answer()
    if isinstance(callback.message, Message):
        await show_admin(callback.message, database, settings)


@admin_router.callback_query(F.data == "admin_orders")
async def admin_orders_callback(callback: CallbackQuery, database: Database, settings: Settings) -> None:
    await callback.answer()
    if isinstance(callback.message, Message):
        await show_admin_orders(callback.message, database, settings)


@admin_router.callback_query(F.data == "admin_stock")
async def admin_stock_callback(callback: CallbackQuery, database: Database, settings: Settings) -> None:
    await callback.answer()
    if isinstance(callback.message, Message):
        await show_stock(callback.message, database, settings)


@admin_router.callback_query(F.data == "admin_products")
async def admin_products_callback(callback: CallbackQuery, database: Database, settings: Settings) -> None:
    await callback.answer()
    if isinstance(callback.message, Message):
        await show_admin_products(callback.message, database, settings)


@admin_router.callback_query(F.data == "admin_help")
async def admin_help_callback(callback: CallbackQuery, settings: Settings) -> None:
    await callback.answer()
    if isinstance(callback.message, Message):
        await send_admin_help(callback.message, settings)


@admin_router.callback_query(F.data.startswith("confirm:"))
async def confirm_callback(callback: CallbackQuery, bot: Bot, database: Database, settings: Settings) -> None:
    await callback.answer()
    if not callback.from_user or callback.from_user.id not in settings.admin_ids:
        return
    if isinstance(callback.message, Message) and callback.data:
        await confirm_order(callback.message, bot, database, callback.data.removeprefix("confirm:"))


@admin_router.callback_query(F.data.startswith("cancel:"))
async def cancel_callback(callback: CallbackQuery, bot: Bot, database: Database, settings: Settings) -> None:
    await callback.answer()
    if not callback.from_user or callback.from_user.id not in settings.admin_ids:
        return
    if isinstance(callback.message, Message) and callback.data:
        await cancel_order(callback.message, bot, database, callback.data.removeprefix("cancel:"))
