import random
import string
import time
from datetime import datetime

from aiogram.types import User


def create_id(prefix: str) -> str:
    stamp = base36(int(time.time() * 1000)).upper()
    suffix = "".join(random.choice(string.ascii_uppercase + string.digits) for _ in range(5))
    return f"{prefix}_{stamp}_{suffix}"


def base36(number: int) -> str:
    alphabet = "0123456789abcdefghijklmnopqrstuvwxyz"
    if number == 0:
        return "0"

    result = ""
    while number:
        number, index = divmod(number, 36)
        result = alphabet[index] + result
    return result


def parse_price(value: str) -> float | None:
    try:
        return float(value.replace(",", "."))
    except ValueError:
        return None


def format_money(amount: float, currency: str) -> str:
    return f"{float(amount):.2f} {currency}"


def format_date(value: str | None) -> str:
    if not value:
        return "-"
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).strftime("%d.%m.%Y %H:%M")
    except ValueError:
        return value


def format_user(user: User) -> str:
    username = f"@{user.username}" if user.username else ""
    name = " ".join(part for part in [user.first_name, user.last_name] if part)
    return " ".join(part for part in [name, username, f"id:{user.id}"] if part)


def human_status(status: str) -> str:
    return {
        "pending_payment": "очікує оплати",
        "payment_review": "оплата на перевірці",
        "delivered": "видано",
        "canceled": "скасовано",
    }.get(status, status)
