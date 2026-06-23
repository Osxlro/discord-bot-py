import logging
from services.core import database

logger = logging.getLogger(__name__)

class StreamAlertRepository:
    @classmethod
    async def exists_alert(cls, guild_id: int, platform: str, channel_name: str) -> bool:
        """Verifica si ya existe una alerta registrada para el canal y plataforma en el servidor."""
        row = await database.fetch_one(
            "SELECT 1 FROM stream_alerts WHERE guild_id = ? AND platform = ? AND channel_name = ?",
            (guild_id, platform, channel_name)
        )
        return row is not None

    @classmethod
    async def add_alert(cls, guild_id: int, platform: str, channel_name: str, discord_channel_id: int, role_id: int = 0, custom_message: str = None):
        """Registra una nueva alerta de stream en la base de datos."""
        await database.execute(
            "INSERT INTO stream_alerts (guild_id, platform, channel_name, discord_channel_id, role_id, custom_message) VALUES (?, ?, ?, ?, ?, ?)",
            (guild_id, platform, channel_name, discord_channel_id, role_id, custom_message)
        )

    @classmethod
    async def remove_alert_by_names(cls, guild_id: int, platform: str, name1: str, name2: str) -> int:
        """Elimina alertas que coincidan con cualquiera de los dos nombres y devuelve el número de filas afectadas."""
        db = await database.get_db()
        cursor = await db.execute(
            "DELETE FROM stream_alerts WHERE guild_id = ? AND platform = ? AND (channel_name = ? OR channel_name = ?)",
            (guild_id, platform, name1, name2)
        )
        await db.commit()
        return cursor.rowcount

    @classmethod
    async def remove_alert(cls, guild_id: int, platform: str, channel_name: str) -> int:
        """Elimina una alerta por su nombre de canal exacto y devuelve el número de filas afectadas."""
        db = await database.get_db()
        cursor = await db.execute(
            "DELETE FROM stream_alerts WHERE guild_id = ? AND platform = ? AND channel_name = ?",
            (guild_id, platform, channel_name)
        )
        await db.commit()
        return cursor.rowcount

    @classmethod
    async def get_stream_alerts(cls, guild_id: int) -> list[dict]:
        """Obtiene todas las alertas configuradas en un servidor."""
        rows = await database.fetch_all(
            "SELECT platform, channel_name, discord_channel_id, role_id, custom_message, last_status FROM stream_alerts WHERE guild_id = ?",
            (guild_id,)
        )
        return [dict(row) for row in rows]

    @classmethod
    async def get_all_stream_alerts(cls) -> list[dict]:
        """Obtiene todas las alertas globales registradas para la tarea en segundo plano."""
        rows = await database.fetch_all(
            "SELECT guild_id, platform, channel_name, discord_channel_id, role_id, custom_message, last_status FROM stream_alerts"
        )
        return [dict(row) for row in rows]

    @classmethod
    async def update_stream_status(cls, guild_id: int, platform: str, channel_name: str, status: str):
        """Actualiza el último estado/video ID notificado para evitar duplicados y refresca el timestamp."""
        await database.execute(
            "UPDATE stream_alerts SET last_status = ?, last_check = datetime('now') WHERE guild_id = ? AND platform = ? AND channel_name = ?",
            (status, guild_id, platform.lower(), channel_name)
        )
