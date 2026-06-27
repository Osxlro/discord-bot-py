import logging
from services.core import database

logger = logging.getLogger(__name__)

class InventoryRepository:
    @classmethod
    async def get_user_inventory(cls, user_id: int) -> dict[str, int]:
        """Retorna un diccionario con los objetos poseídos por el usuario y sus cantidades."""
        rows = await database.fetch_all(
            "SELECT item_id, quantity FROM user_inventory WHERE user_id = ?",
            (user_id,)
        )
        return {row['item_id']: row['quantity'] for row in rows}

    @classmethod
    async def add_item(cls, user_id: int, item_id: str, quantity: int = 1) -> None:
        """Añade o incrementa un objeto en el inventario del usuario."""
        await database.execute(
            "INSERT INTO user_inventory (user_id, item_id, quantity) VALUES (?, ?, ?) "
            "ON CONFLICT(user_id, item_id) DO UPDATE SET quantity = quantity + excluded.quantity",
            (user_id, item_id, quantity)
        )

    @classmethod
    async def remove_item(cls, user_id: int, item_id: str, quantity: int = 1) -> bool:
        """
        Resta una cantidad de un objeto del inventario del usuario.
        Si la cantidad resultante es <= 0, elimina el registro.
        Retorna True si la transacción fue exitosa.
        """
        current_qty = await cls.get_item_count(user_id, item_id)
        if current_qty <= 0:
            return False

        new_qty = current_qty - quantity
        if new_qty <= 0:
            await database.execute(
                "DELETE FROM user_inventory WHERE user_id = ? AND item_id = ?",
                (user_id, item_id)
            )
        else:
            await database.execute(
                "UPDATE user_inventory SET quantity = ? WHERE user_id = ? AND item_id = ?",
                (new_qty, user_id, item_id)
            )
        return True

    @classmethod
    async def get_item_count(cls, user_id: int, item_id: str) -> int:
        """Retorna la cantidad que posee el usuario de un objeto determinado."""
        row = await database.fetch_one(
            "SELECT quantity FROM user_inventory WHERE user_id = ? AND item_id = ?",
            (user_id, item_id)
        )
        return row['quantity'] if row else 0
