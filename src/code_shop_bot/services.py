from datetime import datetime, timezone

from aiogram import Bot
from aiogram.types import Message, User

from .config import Settings
from .database import Database
from .keyboards import (
    admin_order_actions,
    admin_orders_actions,
    catalog_inline_keyboard,
    main_inline_keyboard,
    paid_button,
    product_actions,
)
from .utils import create_id, format_date, format_money, format_user, human_status, parse_price


async def send_main_menu(message: Message, settings: Settings, text: str = "Головне меню:") -> None:
    await message.answer(text, reply_markup=main_inline_keyboard(user_id(message), settings))


async def send_help(message: Message, settings: Settings) -> None:
    await message.answer(
        "\n".join(
            [
                "Команди покупця:",
                "/catalog - список товарів",
                "/orders - твої замовлення",
                "/help - допомога",
                "",
                'Після натискання "Купити" бот створить замовлення. Натисни "Я оплатив", і адміністратор підтвердить оплату.',
                "",
                "Адмін-команди:",
                "/admin - панель адміністратора",
                "/stock - залишки кодів",
                "/addproduct id | Назва | опис | ціна | валюта",
                "/addproducts - багато товарів одним повідомленням",
                "/addcode product_id | CODE-123",
                "/addcodes product_id - багато кодів одним повідомленням",
                "/confirm order_id",
                "/cancel order_id",
            ]
        ),
    )


async def send_admin_help(message: Message, settings: Settings) -> None:
    if not is_admin_message(message, settings):
        await message.answer("Ти не в списку адміністраторів.")
        return

    await message.answer(
        "\n".join(
            [
                "Адмін-команди:",
                "/admin - панель адміністратора",
                "/stock - залишки кодів",
                "/addproduct id | Назва | опис | ціна | валюта",
                "/addproducts - багато товарів одним повідомленням",
                "/addcode product_id | CODE-123",
                "/addcodes product_id - багато кодів одним повідомленням",
                "/confirm order_id",
                "/cancel order_id",
                "",
                "Приклад кодів:",
                "/addcodes steam-10",
                "CODE-001",
                "CODE-002",
                "CODE-003",
                "",
                "Приклад товарів:",
                "/addproducts",
                "steam-10 | Steam $10 | Gift card | 10 | USD",
                "nitro-1 | Discord Nitro | 1 month | 5 | USD",
            ]
        ),
    )


async def show_catalog(message: Message, database: Database, settings: Settings) -> None:
    products = await database.list_products(active_only=True)
    if not products:
        await message.answer(
            "Каталог порожній. Адмін може додати товар через /addproduct.",
        )
        return

    await message.answer(
        "Обери товар:",
        reply_markup=catalog_inline_keyboard(products),
    )


async def show_product(message: Message, database: Database, product_id: str) -> None:
    product = await database.get_product(product_id)
    if not product or not product["active"]:
        await message.answer("Товар не знайдено або вимкнений.")
        return

    await message.answer(
        "\n".join(
            [
                product["title"],
                "",
                product["description"] or "Без опису.",
                "",
                f"Ціна: {format_money(product['price'], product['currency'])}",
                f"В наявності: {product['stock']}",
            ]
        ),
        reply_markup=product_actions(product["id"]),
    )


async def create_order(
    message: Message,
    bot: Bot,
    database: Database,
    settings: Settings,
    product_id: str,
) -> None:
    product = await database.get_product(product_id)
    if not product or not product["active"]:
        await message.answer("Товар не знайдено або вимкнений.")
        return

    if product["stock"] <= 0:
        await message.answer("На жаль, цей товар тимчасово закінчився.")
        return

    user = message.from_user
    if not user:
        await message.answer("Не бачу користувача Telegram для замовлення.")
        return

    order = {
        "id": create_id("ord"),
        "user_id": user.id,
        "chat_id": message.chat.id,
        "username": user.username or "",
        "product_id": product["id"],
        "product_title": product["title"],
        "price": product["price"],
        "currency": product["currency"],
        "status": "pending_payment",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await database.create_order(order)

    await message.answer(
        "\n".join(
            [
                f"Замовлення створено: {order['id']}",
                f"Товар: {product['title']}",
                f"Сума: {format_money(product['price'], product['currency'])}",
                "",
                settings.payment_text,
            ]
        ),
        reply_markup=paid_button(order["id"]),
    )
    await notify_admins(bot, settings, new_order_text(order, user), order["id"])


async def mark_paid(message: Message, bot: Bot, database: Database, settings: Settings, order_id: str) -> None:
    order = await database.get_order(order_id)
    if not order or order["user_id"] != user_id(message):
        await message.answer("Замовлення не знайдено.")
        return

    if order["status"] != "pending_payment":
        await message.answer(f"Поточний статус замовлення: {human_status(order['status'])}.")
        return

    await database.mark_order_paid(order_id)
    await message.answer("Дякую. Передав оплату на перевірку адміністратору.")
    await notify_admins(
        bot,
        settings,
        "\n".join(
            [
                'Покупець натиснув "Я оплатив".',
                f"ID: {order['id']}",
                f"Покупець: @{order['username']}" if order["username"] else f"Покупець: {order['user_id']}",
                f"Товар: {order['product_title']}",
                f"Сума: {format_money(order['price'], order['currency'])}",
            ]
        ),
        order_id,
    )


async def confirm_order(message: Message, bot: Bot, database: Database, order_id: str) -> None:
    order = await database.get_order(order_id)
    if not order:
        await message.answer("Замовлення не знайдено.")
        return
    if order["status"] == "delivered":
        await message.answer("Це замовлення вже видано.")
        return
    if order["status"] == "canceled":
        await message.answer("Це замовлення вже скасовано.")
        return

    code = await database.deliver_order(order_id, order["product_id"])
    if not code:
        await message.answer("На складі немає кодів для цього товару. Додай код через /addcodes.")
        return

    await bot.send_message(
        order["chat_id"],
        "\n".join(
            [
                "Оплату підтверджено.",
                f"Замовлення: {order['id']}",
                f"Товар: {order['product_title']}",
                "",
                "Твій код:",
                code,
            ]
        ),
    )
    await message.answer(f"Замовлення {order['id']} підтверджено, код видано покупцю.")


async def cancel_order(message: Message, bot: Bot, database: Database, order_id: str) -> None:
    order = await database.get_order(order_id)
    if not order:
        await message.answer("Замовлення не знайдено.")
        return
    if order["status"] == "delivered":
        await message.answer("Не можна скасувати вже видане замовлення.")
        return

    await database.cancel_order(order_id)
    await bot.send_message(order["chat_id"], f"Замовлення {order['id']} скасовано.")
    await message.answer(f"Замовлення {order['id']} скасовано.")


async def show_user_orders(message: Message, database: Database, settings: Settings) -> None:
    orders = await database.list_user_orders(user_id(message))
    if not orders:
        await message.answer("У тебе ще немає замовлень.")
        return

    await message.answer(
        "\n\n".join(
            [
                "\n".join(
                    [
                        f"{order['id']} - {human_status(order['status'])}",
                        f"{order['product_title']} - {format_money(order['price'], order['currency'])}",
                        f"Створено: {format_date(order['created_at'])}",
                    ]
                )
                for order in orders
            ]
        ),
    )


async def show_admin(message: Message, database: Database, settings: Settings) -> None:
    if not is_admin_message(message, settings):
        await message.answer("Ти не в списку адміністраторів.")
        return

    counts = await database.order_counts()
    await message.answer(
        "\n".join(
            [
                "Адмін-панель",
                "",
                f"Очікують оплати: {counts.get('pending_payment', 0)}",
                f"На перевірці: {counts.get('payment_review', 0)}",
                f"Видано: {counts.get('delivered', 0)}",
                "",
                "Команди:",
                "/stock",
                "/addproduct id | Назва | опис | ціна | валюта",
                "/addproducts",
                "/addcode product_id | CODE-123",
                "/addcodes product_id",
                "/confirm order_id",
                "/cancel order_id",
            ]
        ),
    )


async def show_admin_orders(message: Message, database: Database, settings: Settings) -> None:
    if not is_admin_message(message, settings):
        await message.answer("Ти не в списку адміністраторів.")
        return

    orders = await database.list_active_orders()
    if not orders:
        await message.answer("Активних замовлень немає.")
        return

    await message.answer(
        "\n\n".join(
            [
                "\n".join(
                    [
                        f"{order['id']} - {human_status(order['status'])}",
                        f"{order['product_title']} - {format_money(order['price'], order['currency'])}",
                        f"Покупець: @{order['username']}" if order["username"] else f"Покупець: {order['user_id']}",
                        f"Створено: {format_date(order['created_at'])}",
                    ]
                )
                for order in orders
            ]
        ),
        reply_markup=admin_orders_actions(orders),
    )


async def show_admin_products(message: Message, database: Database, settings: Settings) -> None:
    if not is_admin_message(message, settings):
        await message.answer("Ти не в списку адміністраторів.")
        return

    products = await database.list_products()
    if not products:
        await message.answer("Товарів ще немає. Додай перший товар командою /addproduct.")
        return

    await message.answer(
        "\n\n".join(
            [
                "\n".join(
                    [
                        f"{'ON' if product['active'] else 'OFF'} {product['id']}",
                        product["title"],
                        f"Ціна: {format_money(product['price'], product['currency'])}",
                        f"Кодів: {product['stock']}",
                    ]
                )
                for product in products
            ]
        ),
    )


async def add_product(message: Message, database: Database) -> None:
    raw = (message.text or "").removeprefix("/addproduct ").strip()
    parsed = parse_product_line(raw)
    if not parsed:
        await message.answer("Формат: /addproduct id | Назва | опис | ціна | валюта")
        return

    product_id, title, description, price, currency = parsed
    added = await database.add_product(product_id, title, description, price, currency)
    if not added:
        await message.answer("Товар з таким id вже існує.")
        return

    await message.answer(f"Товар додано: {title}. Тепер додай коди через /addcodes {product_id}")


async def add_products(message: Message, database: Database) -> None:
    raw = (message.text or "").removeprefix("/addproducts").strip()
    lines = [line.strip() for line in raw.splitlines() if line.strip()]
    if not lines:
        await message.answer("Формат:\n/addproducts\nid | Назва | опис | ціна | валюта")
        return

    added = []
    skipped = []
    for line in lines:
        parsed = parse_product_line(line)
        if not parsed:
            skipped.append(f"{line} - неправильний формат")
            continue
        product_id, title, description, price, currency = parsed
        if await database.add_product(product_id, title, description, price, currency):
            added.append(f"{product_id} - {title}")
        else:
            skipped.append(f"{product_id} - вже існує")

    response = [f"Додано товарів: {len(added)}", *added]
    if skipped:
        response.extend(["", f"Пропущено: {len(skipped)}", *skipped])
    await message.answer("\n".join(response))


async def add_code(message: Message, database: Database) -> None:
    raw = (message.text or "").removeprefix("/addcode ").strip()
    product_id, separator, code = raw.partition("|")
    product = await database.get_product(product_id.strip())
    if not product or not separator or not code.strip():
        await message.answer("Формат: /addcode product_id | CODE-123")
        return

    added, skipped = await database.add_codes(product["id"], [code.strip()])
    await message.answer(
        f"Додано кодів: {added}\nПропущено дублів: {skipped}\nТовар: {product['title']}"
    )


async def add_codes(message: Message, database: Database) -> None:
    raw = (message.text or "").removeprefix("/addcodes").strip()
    if not raw:
        await message.answer(
            "Формат:\n/addcodes product_id\nCODE-001\nCODE-002\n\nАбо:\n/addcodes product_id | CODE-001 | CODE-002"
        )
        return

    lines = raw.splitlines()
    first_line = lines[0].strip()
    product_id = first_line
    codes = lines[1:]
    if "|" in first_line:
        parts = [part.strip() for part in first_line.split("|")]
        product_id = parts[0]
        codes = [*parts[1:], *lines[1:]]

    product = await database.get_product(product_id)
    normalized_codes = [code.strip() for code in codes if code.strip()]
    if not product or not normalized_codes:
        await message.answer("Формат: /addcodes product_id, а нижче кожен код з нового рядка.")
        return

    added, skipped = await database.add_codes(product["id"], normalized_codes)
    product_after = await database.get_product(product["id"])
    await message.answer(
        "\n".join(
            [
                f"Товар: {product['title']}",
                f"Додано кодів: {added}",
                f"Пропущено дублів: {skipped}",
                f"Тепер на складі: {product_after['stock'] if product_after else '?'}",
            ]
        )
    )


async def show_stock(message: Message, database: Database, settings: Settings) -> None:
    if not is_admin_message(message, settings):
        await message.answer("Ти не в списку адміністраторів.")
        return

    products = await database.list_products()
    if not products:
        await message.answer("Товарів ще немає.")
        return

    await message.answer(
        "\n".join(
            [f"{product['id']} - {product['title']}: {product['stock']} код(ів)" for product in products]
        ),
    )


def parse_product_line(line: str) -> tuple[str, str, str, float, str] | None:
    parts = [part.strip() for part in line.split("|")]
    if len(parts) < 5:
        return None
    product_id, title, description, price_text, currency = parts[:5]
    price = parse_price(price_text)
    if not product_id or not title or price is None or price < 0:
        return None
    return product_id, title, description, price, currency or "USD"


async def notify_admins(bot: Bot, settings: Settings, text: str, order_id: str) -> None:
    for admin_id in settings.admin_ids:
        try:
            await bot.send_message(admin_id, text, reply_markup=admin_order_actions(order_id))
        except Exception as error:
            print(f"Failed to notify admin {admin_id}: {error}")


def new_order_text(order: dict, user: User) -> str:
    return "\n".join(
        [
            "Нове замовлення.",
            f"ID: {order['id']}",
            f"Покупець: {format_user(user)}",
            f"Товар: {order['product_title']}",
            f"Сума: {format_money(order['price'], order['currency'])}",
        ]
    )


def is_admin_message(message: Message, settings: Settings) -> bool:
    return user_id(message) in settings.admin_ids


def user_id(message: Message) -> int | None:
    return message.from_user.id if message.from_user else None
