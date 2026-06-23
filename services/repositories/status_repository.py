import logging
from services.core import database

logger = logging.getLogger(__name__)

class StatusRepository:
    @classmethod
    async def get_statuses(cls) -> list[dict]:
        """Obtiene todos los estados rotativos registrados."""
        rows = await database.fetch_all("SELECT id, type, text FROM bot_statuses")
        return [dict(row) for row in rows]

    @classmethod
    async def get_statuses_limited(cls, limit: int) -> list[dict]:
        """Obtiene los últimos N estados ordenados por ID descendente."""
        rows = await database.fetch_all(
            "SELECT id, type, text FROM bot_statuses ORDER BY id DESC LIMIT ?",
            (limit,)
        )
        return [dict(row) for row in rows]

    @classmethod
    async def get_random_status(cls) -> dict | None:
        """Obtiene un estado aleatorio de la base de datos."""
        row = await database.fetch_one("SELECT type, text FROM bot_statuses ORDER BY RANDOM() LIMIT 1")
        return dict(row) if row else None

    @classmethod
    async def add_status(cls, tipo: str, texto: str):
        """Añade un nuevo estado a la base de datos."""
        await database.execute(
            "INSERT INTO bot_statuses (type, text) VALUES (?, ?)",
            (tipo, texto)
        )

    @classmethod
    async def delete_status(cls, status_id: int):
        """Elimina un estado de la base de datos por su ID."""
        await database.execute(
            "DELETE FROM bot_statuses WHERE id = ?",
            (status_id,)
        )
