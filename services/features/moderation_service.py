import re
import discord
import datetime
from ui import moderation_ui
from services.core import db_service, lang_service

# Re-exportar para compatibilidad con otros módulos
get_mod_embed = moderation_ui.get_mod_embed

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

async def handle_clear(channel: discord.TextChannel, amount: int, lang: str):
    """Maneja la lógica de limpieza de mensajes."""
    try:
        deleted = await channel.purge(limit=amount)
        count = len(deleted)
        if count == 0:
            return None, lang_service.get_text("error_old_messages", lang)
        
        return moderation_ui.get_clear_embed(count, lang), None
    except discord.HTTPException:
        return None, lang_service.get_text("error_old_messages", lang)

async def handle_timeout(author: discord.Member, target: discord.Member, time_str: str, reason: str, lang: str):
    """Maneja la lógica de aislamiento (timeout)."""
    if target.top_role >= author.top_role:
        return None, lang_service.get_text("timeout_hierarchy", lang)

    seconds = parse_time(time_str)
    if seconds == 0:
        return None, lang_service.get_text("timeout_invalid", lang)
    
    from config import settings
    limit = settings.CONFIG.get("moderation_config", {}).get("timeout_limit", 2419200)
    if seconds > limit:
        return None, lang_service.get_text("timeout_limit_error", lang)
        
    try:
        duration = datetime.timedelta(seconds=seconds)
        await target.timeout(duration, reason=reason)
        return moderation_ui.get_timeout_embed(target.name, time_str, reason, lang), None
    except Exception as e:
        return None, str(e)

async def handle_untimeout(target: discord.Member, lang: str):
    """Maneja la lógica de retirar aislamiento."""
    try:
        await target.timeout(None, reason="Manual")
        return moderation_ui.get_untimeout_embed(target.name, lang), None
    except Exception as e:
        return None, str(e)

async def handle_kick(author: discord.Member, target: discord.Member, reason: str, lang: str):
    """Maneja la lógica de expulsión."""
    if target.id == author.id:
        return None, lang_service.get_text("error_self_action", lang)
    
    try:
        await target.kick(reason=reason)
        config = await db_service.get_guild_config(author.guild.id)
        return moderation_ui.get_mod_embed(author.guild, target.name, "kick", reason, lang, config), None
    except discord.Forbidden:
        return None, lang_service.get_text("error_hierarchy", lang)
    except Exception as e:
        return None, str(e)

async def handle_ban(author: discord.Member, target: discord.Member, reason: str, lang: str):
    """Maneja la lógica de baneo."""
    if target.id == author.id:
        return None, lang_service.get_text("error_self_action", lang)
    
    try:
        await target.ban(reason=reason)
        config = await db_service.get_guild_config(author.guild.id)
        return moderation_ui.get_mod_embed(author.guild, target.name, "ban", reason, lang, config), None
    except discord.Forbidden:
        return None, lang_service.get_text("error_hierarchy", lang)
    except Exception as e:
        return None, str(e)

async def handle_warn(author: discord.Member, target: discord.Member, reason: str, lang: str):
    """Maneja la lógica de advertencia."""
    if target.id == author.id:
        return None, lang_service.get_text("error_self_action", lang)

    if target.top_role >= author.top_role:
        return None, lang_service.get_text("error_hierarchy", lang)

    count = await add_warn(author.guild.id, target.id, author.id, reason)
    return moderation_ui.get_warn_success_embed(target.name, count, reason, lang), None

async def handle_list_warns(guild: discord.Guild, target: discord.Member, lang: str):
    """Maneja la obtención de advertencias paginadas."""
    warns = await get_warns(guild.id, target.id)
    if not warns:
        return None, lang_service.get_text("warn_list_empty", lang, user=target.name)
    
    pages = moderation_ui.get_warns_pages(guild, target.name, warns, lang)
    return pages, None

async def handle_clear_warns(guild_id: int, target: discord.Member, lang: str):
    """Maneja la limpieza de advertencias."""
    await clear_warns(guild_id, target.id)
    return moderation_ui.get_clear_warns_embed(target.name, lang)

async def handle_delwarn(guild_id: int, warn_id: int, lang: str):
    """Maneja la eliminación de una advertencia específica."""
    success = await delete_warn(guild_id, warn_id)
    if success:
        return moderation_ui.get_delwarn_success_embed(warn_id, lang), None
    else:
        return None, lang_service.get_text("warn_not_found", lang, id=warn_id)