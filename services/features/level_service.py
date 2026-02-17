import discord
import logging
from services.core import db_service, lang_service
from config import settings
from ui import level_ui

logger = logging.getLogger(__name__)

# Re-exportar con envoltura de compatibilidad para HealthCheck/Legacy
async def get_rank_embed(guild, target, lang):
    """Wrapper de compatibilidad para la firma antigua."""
    return await handle_rank(guild, target, lang)

def get_leaderboard_pages(guild, rows, lang):
    """Wrapper de compatibilidad para la firma antigua."""
    return level_ui.get_leaderboard_pages(guild, rows, lang)

async def handle_rank(guild: discord.Guild, target: discord.Member, lang: str):
    """Maneja la lógica para obtener el rango de un usuario."""
    stats = await db_service.fetch_one(
        "SELECT xp, level, rebirths FROM guild_stats WHERE guild_id = ? AND user_id = ?",
        (guild.id, target.id)
    )
    
    if not stats:
        return None

    xp_next = db_service.calculate_xp_required(stats['level'])
    return level_ui.get_rank_embed(target, stats, xp_next, lang)

async def handle_leaderboard(guild: discord.Guild, lang: str):
    """Maneja la lógica para obtener el leaderboard del servidor."""
    limit = settings.LEVELS_CONFIG['LEADERBOARD_LIMIT']
    rows = await db_service.fetch_all(
        "SELECT user_id, level, xp, rebirths FROM guild_stats WHERE guild_id = ? "
        "ORDER BY rebirths DESC, level DESC, xp DESC LIMIT ?", 
        (guild.id, limit)
    )
    
    if not rows:
        return None
        
    return level_ui.get_leaderboard_pages(guild, rows, lang)

async def handle_rebirth(guild_id: int, user_id: int, lang: str):
    """Maneja la lógica para realizar un renacimiento."""
    success, result = await db_service.do_rebirth(guild_id, user_id)
    
    if success:
        return level_ui.get_rebirth_success_embed(lang, result), True
    else:
        return level_ui.get_rebirth_fail_embed(lang, result), False

async def get_level_up_message(member: discord.Member, nuevo_nivel: int, lang: str) -> str:
    """Obtiene y formatea el mensaje de subida de nivel según prioridades (Usuario > Servidor > Default)."""
    user_conf = await db_service.fetch_one("SELECT personal_level_msg FROM users WHERE user_id = ?", (member.id,))
    guild_conf = await db_service.get_guild_config(member.guild.id)
    
    msg_raw = None
    if user_conf and user_conf['personal_level_msg']:
        msg_raw = user_conf['personal_level_msg']
    elif guild_conf.get('server_level_msg'):
        msg_raw = guild_conf['server_level_msg']
    else:
        msg_raw = lang_service.get_text("level_up_default", lang)
    
    return msg_raw.replace("{user}", member.mention)\
                  .replace("{level}", str(nuevo_nivel))\
                  .replace("{server}", member.guild.name)

async def notify_level_up(guild: discord.Guild, member: discord.Member, nuevo_nivel: int, fallback_channel=None):
    """Centraliza la notificación de subida de nivel para eventos y tareas."""
    try:
        lang = await lang_service.get_guild_lang(guild.id)
        config = await db_service.get_guild_config(guild.id)
        msg = await get_level_up_message(member, nuevo_nivel, lang)
        
        # Estrategia de canal: Configurado -> Fallback -> Primer canal disponible
        log_id = config.get('logs_channel_id')
        dest_channel = guild.get_channel(log_id) if log_id else fallback_channel

        if not dest_channel or not dest_channel.permissions_for(guild.me).send_messages:
            # Buscar el primer canal donde el bot pueda hablar si el destino falló
            dest_channel = next((ch for ch in guild.text_channels if ch.permissions_for(guild.me).send_messages), None)
        
        if dest_channel:
            await dest_channel.send(msg)
    except Exception:
        logger.exception("Error notificando nivel")