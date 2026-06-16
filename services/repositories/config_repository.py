import logging
from services.core import database
from services.core.cache_service import cache

logger = logging.getLogger(__name__)

class ConfigRepository:
    @staticmethod
    def _get_cache_key(guild_id: int) -> str:
        return f"guild_config:{guild_id}"

    @classmethod
    async def get_guild_config(cls, guild_id: int) -> dict:
        """Obtiene la configuración específica de un servidor (con caché)."""
        cache_key = cls._get_cache_key(guild_id)
        cached = await cache.get(cache_key)
        if cached is not None:
            return cached

        # Si no está en caché, leemos de la base de datos
        row = await database.fetch_one("SELECT * FROM guild_config WHERE guild_id = ?", (guild_id,))
        if row:
            config = dict(row)
        else:
            # Si no existe, inicializamos con los valores por defecto y guardamos en DB
            await database.execute("INSERT OR IGNORE INTO guild_config (guild_id) VALUES (?)", (guild_id,))
            new_row = await database.fetch_one("SELECT * FROM guild_config WHERE guild_id = ?", (guild_id,))
            config = dict(new_row) if new_row else {}

        # Guardar en caché
        await cache.set(cache_key, config)
        return config

    @classmethod
    async def update_guild_config(cls, guild_id: int, updates: dict):
        """Actualiza la configuración en DB y refresca el caché."""
        if not updates:
            return

        set_clause = ", ".join(f"{col} = ?" for col in updates.keys())
        params = list(updates.values()) + [guild_id]
        
        await database.execute(f"UPDATE guild_config SET {set_clause} WHERE guild_id = ?", tuple(params))
        
        # Invalida o actualiza la caché
        cache_key = cls._get_cache_key(guild_id)
        current = await cls.get_guild_config(guild_id)
        current.update(updates)
        await cache.set(cache_key, current)

    @classmethod
    async def clear_cache(cls, guild_id: int = None):
        if guild_id:
            await cache.delete(cls._get_cache_key(guild_id))
        else:
            # Limpiar caché completo (no es muy usado en prod pero sí en pruebas/desarrollo)
            pass
