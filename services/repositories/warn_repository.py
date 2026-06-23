import logging
from services.core import database

logger = logging.getLogger(__name__)

class WarnRepository:
    @classmethod
    async def add_warn(cls, guild_id: int, user_id: int, mod_id: int, reason: str) -> int:
        """Registra una advertencia para un usuario y devuelve el total actual de advertencias."""
        await database.execute(
            "INSERT INTO warns (guild_id, user_id, mod_id, reason) VALUES (?, ?, ?, ?)",
            (guild_id, user_id, mod_id, reason)
        )
        row = await database.fetch_one(
            "SELECT COUNT(*) as count FROM warns WHERE guild_id = ? AND user_id = ?",
            (guild_id, user_id)
        )
        return row['count'] if row else 0

    @classmethod
    async def get_warns(cls, guild_id: int, user_id: int) -> list[dict]:
        """Obtiene el historial de advertencias de un usuario en un servidor."""
        rows = await database.fetch_all(
            "SELECT id, mod_id, reason, timestamp FROM warns WHERE guild_id = ? AND user_id = ? ORDER BY timestamp DESC",
            (guild_id, user_id)
        )
        return [dict(row) for row in rows]

    @classmethod
    async def clear_warns(cls, guild_id: int, user_id: int):
        """Elimina todas las advertencias de un usuario en un servidor."""
        await database.execute(
            "DELETE FROM warns WHERE guild_id = ? AND user_id = ?",
            (guild_id, user_id)
        )

    @classmethod
    async def delete_warn(cls, guild_id: int, warn_id: int) -> bool:
        """Elimina una advertencia específica si existe en el servidor indicado."""
        row = await database.fetch_one(
            "SELECT id FROM warns WHERE id = ? AND guild_id = ?",
            (warn_id, guild_id)
        )
        if not row:
            return False
        await database.execute(
            "DELETE FROM warns WHERE id = ? AND guild_id = ?",
            (warn_id, guild_id)
        )
        return True
