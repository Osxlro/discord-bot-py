import discord
import logging
from config import settings
from services.utils import embed_service
from services.core import lang_service

logger = logging.getLogger(__name__)

def get_rank_embed(target: discord.Member, stats: dict, xp_next: int, lang: str) -> discord.Embed:
    """Genera un embed con el nivel, progreso y rebirths del usuario."""
    level = stats['level']
    xp = stats['xp']
    rebirths = stats['rebirths']
    
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

def get_rebirth_success_embed(lang: str, rebirths: int) -> discord.Embed:
    """Genera el embed de éxito para un renacimiento."""
    title = lang_service.get_text("rebirth_title_success", lang)
    msg = lang_service.get_text("rebirth_success", lang, rebirths=rebirths)
    return embed_service.success(title, msg)

def get_rebirth_fail_embed(lang: str, result: any) -> discord.Embed:
    """Genera el embed de error para un renacimiento."""
    title = lang_service.get_text("rebirth_title_fail", lang)
    if result == "no_data":
        msg = lang_service.get_text("rank_no_data", lang)
    elif isinstance(result, int):
        msg = lang_service.get_text("rebirth_fail_level", lang, level=result)
    else:
        msg = lang_service.get_text("rebirth_fail_generic", lang)
    
    return embed_service.error(title, msg)