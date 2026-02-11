import discord
from config import settings
from services import lang_service, embed_service, db_service
import logging

logger = logging.getLogger(__name__)

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
        
        # 1. Intentar canal de logs
        dest_channel = None
        if config.get('logs_channel_id'):
            dest_channel = guild.get_channel(config['logs_channel_id'])
        
        # 2. Si no hay logs, usar el fallback (donde escribió el usuario)
        if not dest_channel:
            dest_channel = fallback_channel
            
        # 3. Si sigue sin haber canal, buscar el primero con permisos
        if not dest_channel:
            for text_channel in guild.text_channels:
                perms = text_channel.permissions_for(guild.me)
                if perms.send_messages:
                    dest_channel = text_channel
                    break
        
        if dest_channel:
            await dest_channel.send(msg)
    except Exception:
        logger.exception("Error notificando nivel")

def get_leaderboard_pages(guild: discord.Guild, rows: list, lang: str) -> list[discord.Embed]:
    """Procesa los datos de la DB y genera los embeds paginados para el ranking."""
    chunk_size = settings.LEVELS_CONFIG["LEADERBOARD_CHUNK_SIZE"]
    chunks = [rows[i:i + chunk_size] for i in range(0, len(rows), chunk_size)]
    pages = []

    title = lang_service.get_text("leaderboard_title", lang, server=guild.name)
    medals = settings.LEVELS_CONFIG['MEDALS']

    for i, chunk in enumerate(chunks):
        lines = []
        start_rank = (i * chunk_size) + 1
        
        for j, row in enumerate(chunk, start=start_rank):
            user_id = row['user_id']
            member = guild.get_member(user_id)
            
            # Escapamos markdown para evitar que nombres con guiones bajos rompan el formato
            name = discord.utils.escape_markdown(member.display_name) if member else f"Usuario {user_id}"
            
            rebirth_text = f"🌀 {row['rebirths']} | " if row['rebirths'] > 0 else ""
            xp_fmt = f"{row['xp']:,}"
            
            if j <= 3:
                medal = medals[j-1]
                prefix = "👑" if j == 1 else ("🛡️" if j == 2 else "⚔️")
                lines.append(f"{medal} **{name}**\n> {prefix} {rebirth_text}Nvl **{row['level']}** • ✨ `{xp_fmt}` XP")
            else:
                lines.append(f"`#{j}` **{name}** • {rebirth_text}Nvl {row['level']} • `{xp_fmt}` XP")
        
        desc = "\n\n".join(lines)
        embed = embed_service.info(title, desc, thumbnail=guild.icon.url if guild.icon else None)
        embed.set_footer(text=lang_service.get_text("leaderboard_footer", lang, current=i+1, total=len(chunks)))
        pages.append(embed)

    return pages