import logging
from services.core import database
from services.core.cache_service import cache

logger = logging.getLogger(__name__)

class UserRepository:
    @staticmethod
    def _get_prefix_cache_key(user_id: int) -> str:
        return f"user_prefix:{user_id}"

    @classmethod
    async def get_user_prefix(cls, user_id: int) -> str | None:
        """Obtiene el prefijo personalizado de un usuario (con caché)."""
        cache_key = cls._get_prefix_cache_key(user_id)
        cached = await cache.get(cache_key)
        if cached is not None:
            # Si se guardó como 'none', retornamos None
            return None if cached == "none" else cached

        row = await database.fetch_one("SELECT custom_prefix FROM users WHERE user_id = ?", (user_id,))
        prefix = row['custom_prefix'] if row else None
        
        # Guardamos en caché
        await cache.set(cache_key, prefix if prefix is not None else "none")
        return prefix

    @classmethod
    async def set_user_prefix(cls, user_id: int, prefix: str | None):
        """Establece o elimina el prefijo de usuario en DB e invalida caché."""
        await database.execute(
            "INSERT INTO users (user_id, custom_prefix) VALUES (?, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET custom_prefix = excluded.custom_prefix",
            (user_id, prefix)
        )
        cache_key = cls._get_prefix_cache_key(user_id)
        await cache.set(cache_key, prefix if prefix is not None else "none")

    @classmethod
    async def get_user_coins(cls, user_id: int) -> int:
        """Retorna las monedas globales del usuario."""
        row = await database.fetch_one("SELECT coins FROM users WHERE user_id = ?", (user_id,))
        return row['coins'] if row else 0

    @classmethod
    async def add_user_coins(cls, user_id: int, amount: int):
        """Añade o resta monedas al saldo del usuario."""
        await database.execute(
            "INSERT INTO users (user_id, coins) VALUES (?, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET coins = coins + excluded.coins",
            (user_id, amount)
        )

    @classmethod
    async def set_user_coins(cls, user_id: int, amount: int):
        """Establece directamente las monedas globales del usuario."""
        await database.execute(
            "INSERT INTO users (user_id, coins) VALUES (?, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET coins = excluded.coins",
            (user_id, amount)
        )

    @classmethod
    async def get_user_data(cls, user_id: int) -> dict | None:
        """Obtiene toda la información de perfil y preferencias de un usuario en base de datos."""
        row = await database.fetch_one("SELECT * FROM users WHERE user_id = ?", (user_id,))
        return dict(row) if row else None
