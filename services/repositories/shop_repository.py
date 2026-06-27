import logging
from services.core import database

logger = logging.getLogger(__name__)

class ShopRepository:
    @classmethod
    async def get_all_items(cls) -> list[dict]:
        """Obtiene todos los objetos del catálogo de la tienda de la base de datos."""
        rows = await database.fetch_all("SELECT * FROM shop_items")
        return [dict(row) for row in rows]

    @classmethod
    async def get_item(cls, item_id: str) -> dict | None:
        """Obtiene un objeto por su ID."""
        row = await database.fetch_one("SELECT * FROM shop_items WHERE item_id = ?", (item_id,))
        return dict(row) if row else None

    @classmethod
    async def add_or_update_item(
        cls,
        item_id: str,
        emoji: str,
        cost: int,
        availability: str = "permanent",
        start_date: str | None = None,
        end_date: str | None = None,
        purchase_limit: int | None = None,
        total_stock: int | None = None,
        name_default: str | None = None,
        desc_default: str | None = None,
        category: str = "Otros"
    ) -> None:
        """Añade o actualiza la configuración de un objeto en la tienda."""
        await database.execute(
            "INSERT INTO shop_items (item_id, emoji, cost, availability, start_date, end_date, purchase_limit, total_stock, name_default, desc_default, category) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(item_id) DO UPDATE SET "
            "emoji = excluded.emoji, cost = excluded.cost, availability = excluded.availability, "
            "start_date = excluded.start_date, end_date = excluded.end_date, "
            "purchase_limit = excluded.purchase_limit, total_stock = excluded.total_stock, "
            "name_default = excluded.name_default, desc_default = excluded.desc_default, "
            "category = excluded.category",
            (item_id, emoji, cost, availability, start_date, end_date, purchase_limit, total_stock, name_default, desc_default, category)
        )

    @classmethod
    async def delete_item(cls, item_id: str) -> bool:
        """Elimina un objeto de la tienda por su ID."""
        row = await cls.get_item(item_id)
        if not row:
            return False
        await database.execute("DELETE FROM shop_items WHERE item_id = ?", (item_id,))
        return True

    @classmethod
    async def get_global_sales(cls, item_id: str) -> int:
        """Suma la cantidad total vendida de este objeto a nivel global."""
        row = await database.fetch_one(
            "SELECT SUM(quantity) as total FROM user_inventory WHERE item_id = ?",
            (item_id,)
        )
        return row['total'] if row and row['total'] else 0
