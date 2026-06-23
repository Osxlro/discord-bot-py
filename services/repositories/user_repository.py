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

    @classmethod
    async def update_description(cls, user_id: int, description: str):
        """Actualiza la descripción de la biografía de perfil del usuario."""
        await database.execute(
            "INSERT INTO users (user_id, description) VALUES (?, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET description = excluded.description",
            (user_id, description)
        )

    @classmethod
    async def update_personal_message(cls, user_id: int, msg_type: str, text: str | None):
        """Actualiza el mensaje personalizado de nivel o de cumpleaños de un usuario."""
        column = "personal_level_msg" if msg_type == "Nivel" else "personal_birthday_msg"
        await database.execute(
            f"INSERT INTO users (user_id, {column}) VALUES (?, ?) "
            f"ON CONFLICT(user_id) DO UPDATE SET {column} = excluded.{column}",
            (user_id, text)
        )

    @classmethod
    async def update_gender(cls, user_id: int, gender: str | None):
        """Actualiza el género de perfil de un usuario."""
        await database.execute(
            "INSERT INTO users (user_id, gender) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET gender = excluded.gender",
            (user_id, gender)
        )

    @classmethod
    async def set_user_birthday(cls, user_id: int, birthday: str | None, celebrate: bool = True):
        """Establece o elimina el cumpleaños de un usuario, y activa la felicitación si se establece."""
        if birthday is None:
            await database.execute("UPDATE users SET birthday = NULL WHERE user_id = ?", (user_id,))
        else:
            await database.execute(
                "INSERT INTO users (user_id, birthday, celebrate) VALUES (?, ?, ?) "
                "ON CONFLICT(user_id) DO UPDATE SET birthday = excluded.birthday, celebrate = excluded.celebrate",
                (user_id, birthday, 1 if celebrate else 0)
            )

    @classmethod
    async def set_user_celebrate(cls, user_id: int, celebrate: bool):
        """Establece si el usuario desea que se celebre su cumpleaños."""
        await database.execute(
            "UPDATE users SET celebrate = ? WHERE user_id = ?",
            (1 if celebrate else 0, user_id)
        )

    @classmethod
    async def get_users_with_birthday(cls, birthday_str: str) -> list[dict]:
        """Obtiene la lista de usuarios que cumplen años hoy y tienen activada la celebración."""
        rows = await database.fetch_all(
            "SELECT user_id, personal_birthday_msg FROM users WHERE birthday = ? AND celebrate = 1",
            (birthday_str,)
        )
        return [dict(row) for row in rows]

    @classmethod
    async def get_all_active_birthdays(cls) -> list[dict]:
        """Obtiene la lista de todos los cumpleaños activos registrados (birthday no nulo y celebrate=1)."""
        rows = await database.fetch_all(
            "SELECT user_id, birthday FROM users WHERE birthday IS NOT NULL AND celebrate = 1"
        )
        return [dict(row) for row in rows]

