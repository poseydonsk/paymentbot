from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from .config import Settings
from .database import product_button_text


class Buttons:
    catalog = "Каталог"
    orders = "Мої замовлення"
    help = "Допомога"
    main_menu = "Головне меню"
    admin = "Адмін-панель"
    admin_orders = "Адмін: Замовлення"
    admin_stock = "Адмін: Склад"
    admin_products = "Адмін: Товари"
    admin_help = "Адмін: Допомога"


def main_inline_keyboard(user_id: int | None, settings: Settings) -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton(text=Buttons.catalog, callback_data="catalog"),
            InlineKeyboardButton(text=Buttons.orders, callback_data="orders"),
        ],
        [InlineKeyboardButton(text=Buttons.help, callback_data="help")],
    ]

    if user_id in settings.admin_ids:
        keyboard.extend(
            [
                [InlineKeyboardButton(text=Buttons.admin, callback_data="admin")],
                [
                    InlineKeyboardButton(text=Buttons.admin_orders, callback_data="admin_orders"),
                    InlineKeyboardButton(text=Buttons.admin_stock, callback_data="admin_stock"),
                ],
                [
                    InlineKeyboardButton(text=Buttons.admin_products, callback_data="admin_products"),
                    InlineKeyboardButton(text=Buttons.admin_help, callback_data="admin_help"),
                ],
            ]
        )

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def catalog_inline_keyboard(products: list) -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton(text=product_button_text(product), callback_data=f"product:{product['id']}")]
        for product in products
    ]
    keyboard.append([InlineKeyboardButton(text=Buttons.main_menu, callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def product_actions(product_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Купити", callback_data=f"buy:{product_id}")],
            [InlineKeyboardButton(text="Назад до каталогу", callback_data="catalog")],
        ]
    )


def paid_button(order_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Я оплатив", callback_data=f"paid:{order_id}")]]
    )


def admin_order_actions(order_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Підтвердити", callback_data=f"confirm:{order_id}"),
                InlineKeyboardButton(text="Скасувати", callback_data=f"cancel:{order_id}"),
            ]
        ]
    )


def admin_orders_actions(orders: list) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=f"Підтвердити {order['id']}", callback_data=f"confirm:{order['id']}"),
                InlineKeyboardButton(text=f"Скасувати {order['id']}", callback_data=f"cancel:{order['id']}"),
            ]
            for order in orders
        ]
    )
