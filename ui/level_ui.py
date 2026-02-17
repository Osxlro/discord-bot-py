import discord
import logging
from config import settings
from services.utils import embed_service
from services.core import db_service, lang_service

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

async def get_rank_embed(guild: discord.Guild, target: discord.Member, lang: str) -> discord.Embed:
    """Genera un embed con el nivel, progreso y rebirths del usuario."""
    stats = await db_service.fetch_one(
        "SELECT xp, level, rebirths FROM guild_stats WHERE guild_id = ? AND user_id = ?",
        (guild.id, target.id)
    )
    
    if not stats:
        return None

    level = stats['level']
    xp = stats['xp']
    rebirths = stats['rebirths']
    
    xp_next = db_service.calculate_xp_required(level)
    progress = min(xp / xp_next, 1.0) if xp_next > 0 else 1.0
    
    bar_len = settings.UI_CONFIG["PROFILE_BAR_LENGTH"]
    filled = int(progress * bar_len)
    bar = settings.UI_CONFIG["PROGRESS_BAR_FILLED"] * filled + settings.UI_CONFIG["PROGRESS_BAR_EMPTY"] * (bar_len - filled)

    title = lang_service.get_text("rank_title", lang, user=target.display_name)
    lvl_label = lang_service.get_text("profile_field_lvl", lang)
    reb_label = lang_service.get_text("profile_field_rebirths", lang)
    xp_label = lang_service.get_text("profile_field_xp", lang)
    
    description = (
        f"{lvl_label}: **{level}**\n"
        f"{reb_label}: **{rebirths}**\n"
        f"{xp_label}: **{xp:,} / {xp_next:,}**\n\n"
        f"`{bar}` **{int(progress * 100)}%**"
    )
    
    return embed_service.info(title, description, thumbnail=target.display_avatar.url)

def get_leaderboard_pages(guild: discord.Guild, rows: list, lang: str) -> list[discord.Embed]:
    """Procesa los datos de la DB y genera los embeds paginados para el ranking."""
    chunk_size = settings.LEVELS_CONFIG["LEADERBOARD_CHUNK_SIZE"]
    chunks = [rows[i:i + chunk_size] for i in range(0, len(rows), chunk_size)]
    pages = []
    title = lang_service.get_text("leaderboard_title", lang, server=guild.name)
    medals = settings.LEVELS_CONFIG['MEDALS']

    for i, chunk in enumerate(chunks):
        lines = []
        for j, row in enumerate(chunk, start=(i * chunk_size) + 1):
            member = guild.get_member(row['user_id'])
            name = discord.utils.escape_markdown(member.display_name) if member else f"Usuario {row['user_id']}"
            rebirth_text = f"🌀 {row['rebirths']} | " if row['rebirths'] > 0 else ""
            xp_fmt = f"{row['xp']:,}"
            
            if j <= 3:
                medal = medals[j-1]
                prefix = "👑" if j == 1 else ("🛡️" if j == 2 else "⚔️")
                lines.append(f"{medal} **{name}**\n> {prefix} {rebirth_text}Nvl **{row['level']}** • ✨ `{xp_fmt}` XP")
            else:
                lines.append(f"`#{j}` **{name}** • {rebirth_text}Nvl {row['level']} • `{xp_fmt}` XP")
        
        embed = embed_service.info(title, "\n\n".join(lines), thumbnail=guild.icon.url if guild.icon else None)
        embed.set_footer(text=lang_service.get_text("leaderboard_footer", lang, current=i+1, total=len(chunks)))
        pages.append(embed)
    return pages