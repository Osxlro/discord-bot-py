import re
from ui.moderation_ui import get_mod_embed
from services.core import db_service

# Re-exportar para compatibilidad con otros módulos
get_mod_embed = get_mod_embed

def parse_time(time_str: str) -> int:
    """Convierte una cadena de tiempo (1h, 10m) en segundos."""
    time_regex = re.compile(r"(\d+)([smhd])")
    match = time_regex.match(time_str.lower())
    if not match:
        return 0
    val, unit = match.groups()
    val = int(val)
    if unit == 's': return val
    if unit == 'm': return val * 60
    if unit == 'h': return val * 3600
    if unit == 'd': return val * 86400
    return 0

async def add_warn(guild_id: int, user_id: int, mod_id: int, reason: str) -> int:
    """Añade una advertencia y retorna el total actual."""
    await db_service.execute(
        "INSERT INTO warns (guild_id, user_id, mod_id, reason) VALUES (?, ?, ?, ?)",
        (guild_id, user_id, mod_id, reason)
    )
    row = await db_service.fetch_one(
        "SELECT COUNT(*) as count FROM warns WHERE guild_id = ? AND user_id = ?",
        (guild_id, user_id)
    )
    return row['count'] if row else 0

async def get_warns(guild_id: int, user_id: int):
    """Obtiene el historial de advertencias."""
    return await db_service.fetch_all(
        "SELECT id, mod_id, reason, timestamp FROM warns WHERE guild_id = ? AND user_id = ? ORDER BY timestamp DESC",
        (guild_id, user_id)
    )

async def clear_warns(guild_id: int, user_id: int):
    """Elimina todas las advertencias de un usuario."""
    await db_service.execute("DELETE FROM warns WHERE guild_id = ? AND user_id = ?", (guild_id, user_id))

async def delete_warn(guild_id: int, warn_id: int) -> bool:
    """Elimina una advertencia específica por su ID."""
    row = await db_service.fetch_one("SELECT id FROM warns WHERE id = ? AND guild_id = ?", (warn_id, guild_id))
    if not row:
        return False
    
    await db_service.execute("DELETE FROM warns WHERE id = ? AND guild_id = ?", (warn_id, guild_id))
    return True