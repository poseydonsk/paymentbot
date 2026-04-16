import json
from pathlib import Path
from typing import Any

import aiosqlite


class Database:
    def __init__(self, path: Path):
        self.path = path
        self.connection: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        self.connection = await aiosqlite.connect(self.path)
        self.connection.row_factory = aiosqlite.Row
        await self.execute("PRAGMA journal_mode=WAL")
        await self.execute("PRAGMA foreign_keys=ON")

    async def close(self) -> None:
        if self.connection:
            await self.connection.close()

    async def setup(self) -> None:
        await self.executescript(
            """
            CREATE TABLE IF NOT EXISTS products (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                price REAL NOT NULL DEFAULT 0,
                currency TEXT NOT NULL DEFAULT 'USD',
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS codes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id TEXT NOT NULL,
                code TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'available',
                order_id TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                delivered_at TEXT,
                UNIQUE(product_id, code),
                FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS orders (
                id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                chat_id INTEGER NOT NULL,
                username TEXT NOT NULL DEFAULT '',
                product_id TEXT NOT NULL,
                product_title TEXT NOT NULL,
                price REAL NOT NULL,
                currency TEXT NOT NULL,
                status TEXT NOT NULL,
                code TEXT,
                created_at TEXT NOT NULL,
                paid_at TEXT,
                delivered_at TEXT,
                canceled_at TEXT
            );

            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT NOT NULL DEFAULT '',
                first_name TEXT NOT NULL DEFAULT '',
                last_name TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            """
        )

    async def import_legacy_json(self, legacy_path: Path) -> None:
        imported = await self.get_meta("legacy_json_imported")
        if imported or not legacy_path.exists():
            return

        raw = json.loads(legacy_path.read_text(encoding="utf-8"))

        for product in raw.get("products", []):
            await self.upsert_product(
                product_id=str(product.get("id", "")),
                title=str(product.get("title", "")),
                description=str(product.get("description", "")),
                price=float(product.get("price") or 0),
                currency=str(product.get("currency") or "USD"),
                active=product.get("active") is not False,
            )
            await self.add_codes(str(product.get("id", "")), [str(code) for code in product.get("codes", [])])

        for order in raw.get("orders", []):
            await self.execute(
                """
                INSERT OR IGNORE INTO orders (
                    id, user_id, chat_id, username, product_id, product_title, price, currency,
                    status, code, created_at, paid_at, delivered_at, canceled_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    order.get("id"),
                    order.get("userId"),
                    order.get("chatId"),
                    order.get("username") or "",
                    order.get("productId"),
                    order.get("productTitle") or "",
                    float(order.get("price") or 0),
                    order.get("currency") or "USD",
                    order.get("status") or "pending_payment",
                    order.get("code"),
                    order.get("createdAt"),
                    order.get("paidAt"),
                    order.get("deliveredAt"),
                    order.get("canceledAt"),
                ),
            )

        await self.set_meta("legacy_json_imported", "1")
        await self.commit()

    async def touch_user(self, user: Any) -> None:
        await self.execute(
            """
            INSERT INTO users (id, username, first_name, last_name)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                username = excluded.username,
                first_name = excluded.first_name,
                last_name = excluded.last_name,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                user.id,
                user.username or "",
                user.first_name or "",
                user.last_name or "",
            ),
        )
        await self.commit()

    async def list_products(self, active_only: bool = False) -> list[aiosqlite.Row]:
        if active_only:
            return await self.fetchall(
                """
                SELECT p.*, COUNT(c.id) AS stock
                FROM products p
                LEFT JOIN codes c ON c.product_id = p.id AND c.status = 'available'
                WHERE p.active = 1
                GROUP BY p.id
                ORDER BY p.title
                """
            )
        return await self.fetchall(
            """
            SELECT p.*, COUNT(c.id) AS stock
            FROM products p
            LEFT JOIN codes c ON c.product_id = p.id AND c.status = 'available'
            GROUP BY p.id
            ORDER BY p.title
            """
        )

    async def get_product(self, product_id: str) -> aiosqlite.Row | None:
        return await self.fetchone(
            """
            SELECT p.*, COUNT(c.id) AS stock
            FROM products p
            LEFT JOIN codes c ON c.product_id = p.id AND c.status = 'available'
            WHERE p.id = ?
            GROUP BY p.id
            """,
            (product_id,),
        )

    async def find_product_by_button(self, button_text: str) -> aiosqlite.Row | None:
        for product in await self.list_products(active_only=True):
            if product_button_text(product) == button_text:
                return product
        return None

    async def upsert_product(
        self,
        product_id: str,
        title: str,
        description: str,
        price: float,
        currency: str,
        active: bool = True,
    ) -> None:
        await self.execute(
            """
            INSERT OR IGNORE INTO products (id, title, description, price, currency, active)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (product_id, title, description, price, currency, int(active)),
        )

    async def add_product(
        self,
        product_id: str,
        title: str,
        description: str,
        price: float,
        currency: str,
    ) -> bool:
        cursor = await self.execute(
            """
            INSERT OR IGNORE INTO products (id, title, description, price, currency, active)
            VALUES (?, ?, ?, ?, ?, 1)
            """,
            (product_id, title, description, price, currency),
        )
        await self.commit()
        return cursor.rowcount > 0

    async def add_codes(self, product_id: str, codes: list[str]) -> tuple[int, int]:
        added = 0
        skipped = 0
        for code in codes:
            cursor = await self.execute(
                "INSERT OR IGNORE INTO codes (product_id, code) VALUES (?, ?)",
                (product_id, code),
            )
            if cursor.rowcount:
                added += 1
            else:
                skipped += 1
        await self.commit()
        return added, skipped

    async def create_order(self, order: dict[str, Any]) -> None:
        await self.execute(
            """
            INSERT INTO orders (
                id, user_id, chat_id, username, product_id, product_title, price, currency,
                status, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                order["id"],
                order["user_id"],
                order["chat_id"],
                order["username"],
                order["product_id"],
                order["product_title"],
                order["price"],
                order["currency"],
                order["status"],
                order["created_at"],
            ),
        )
        await self.commit()

    async def get_order(self, order_id: str) -> aiosqlite.Row | None:
        return await self.fetchone("SELECT * FROM orders WHERE id = ?", (order_id,))

    async def list_user_orders(self, user_id: int) -> list[aiosqlite.Row]:
        return await self.fetchall(
            "SELECT * FROM orders WHERE user_id = ? ORDER BY created_at DESC LIMIT 10",
            (user_id,),
        )

    async def list_active_orders(self) -> list[aiosqlite.Row]:
        return await self.fetchall(
            """
            SELECT * FROM orders
            WHERE status IN ('pending_payment', 'payment_review')
            ORDER BY created_at DESC
            LIMIT 10
            """
        )

    async def mark_order_paid(self, order_id: str) -> None:
        await self.execute(
            "UPDATE orders SET status = 'payment_review', paid_at = CURRENT_TIMESTAMP WHERE id = ?",
            (order_id,),
        )
        await self.commit()

    async def deliver_order(self, order_id: str, product_id: str) -> str | None:
        await self.execute("BEGIN IMMEDIATE")
        code_row = await self.fetchone(
            """
            SELECT id, code FROM codes
            WHERE product_id = ? AND status = 'available'
            ORDER BY id
            LIMIT 1
            """,
            (product_id,),
        )
        if not code_row:
            await self.execute("ROLLBACK")
            return None

        await self.execute(
            """
            UPDATE codes
            SET status = 'delivered', order_id = ?, delivered_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (order_id, code_row["id"]),
        )
        await self.execute(
            """
            UPDATE orders
            SET status = 'delivered', code = ?, delivered_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (code_row["code"], order_id),
        )
        await self.execute("COMMIT")
        return str(code_row["code"])

    async def cancel_order(self, order_id: str) -> None:
        await self.execute(
            "UPDATE orders SET status = 'canceled', canceled_at = CURRENT_TIMESTAMP WHERE id = ?",
            (order_id,),
        )
        await self.commit()

    async def order_counts(self) -> dict[str, int]:
        rows = await self.fetchall("SELECT status, COUNT(*) AS count FROM orders GROUP BY status")
        return {row["status"]: row["count"] for row in rows}

    async def get_meta(self, key: str) -> str | None:
        row = await self.fetchone("SELECT value FROM meta WHERE key = ?", (key,))
        return str(row["value"]) if row else None

    async def set_meta(self, key: str, value: str) -> None:
        await self.execute(
            "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
            (key, value),
        )

    async def execute(self, query: str, params: tuple[Any, ...] = ()) -> aiosqlite.Cursor:
        if not self.connection:
            raise RuntimeError("Database is not connected")
        return await self.connection.execute(query, params)

    async def executescript(self, script: str) -> None:
        if not self.connection:
            raise RuntimeError("Database is not connected")
        await self.connection.executescript(script)
        await self.connection.commit()

    async def fetchone(self, query: str, params: tuple[Any, ...] = ()) -> aiosqlite.Row | None:
        cursor = await self.execute(query, params)
        return await cursor.fetchone()

    async def fetchall(self, query: str, params: tuple[Any, ...] = ()) -> list[aiosqlite.Row]:
        cursor = await self.execute(query, params)
        return await cursor.fetchall()

    async def commit(self) -> None:
        if not self.connection:
            raise RuntimeError("Database is not connected")
        await self.connection.commit()


def product_button_text(product: aiosqlite.Row) -> str:
    return f"{product['title']} - {float(product['price']):.2f} {product['currency']}"
