import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "data"


@dataclass(frozen=True)
class Settings:
    bot_token: str
    admin_ids: set[int]
    store_name: str
    payment_text: str
    database_path: Path
    legacy_json_path: Path


def load_settings() -> Settings:
    load_dotenv(ROOT_DIR / ".env")

    bot_token = os.getenv("BOT_TOKEN", "").strip()
    if not bot_token:
        raise RuntimeError("BOT_TOKEN is missing. Add it to .env")

    admin_ids = {
        int(item.strip())
        for item in os.getenv("ADMIN_IDS", "").split(",")
        if item.strip().isdigit()
    }

    return Settings(
        bot_token=bot_token,
        admin_ids=admin_ids,
        store_name=os.getenv("STORE_NAME", "Code Shop").strip() or "Code Shop",
        payment_text=os.getenv(
            "PAYMENT_TEXT",
            'Send payment and press "I paid". Admin will confirm the order.',
        ),
        database_path=DATA_DIR / "shop_v2.sqlite3",
        legacy_json_path=DATA_DIR / "db.json",
    )
