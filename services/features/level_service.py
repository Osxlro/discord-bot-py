import discord
import logging
from services.core import db_service, lang_service
from ui import level_ui

logger = logging.getLogger(__name__)

# Re-exportar para compatibilidad con tareas y comandos
get_rank_embed = level_ui.get_rank_embed
get_leaderboard_pages = level_ui.get_leaderboard_pages
get_level_up_message = level_ui.get_level_up_message

async def notify_level_up(guild: discord.Guild, member: discord.Member, nuevo_nivel: int, fallback_channel=None):
    """Centraliza la notificación de subida de nivel para eventos y tareas."""
    try:
        lang = await lang_service.get_guild_lang(guild.id)
        config = await db_service.get_guild_config(guild.id)
        msg = await level_ui.get_level_up_message(member, nuevo_nivel, lang)
        
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