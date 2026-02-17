import discord
import datetime
from services.utils import embed_service
from services.core import lang_service
from config import settings

def get_mod_embed(guild: discord.Guild, user_name: str, action: str, reason: str, lang: str, config: dict) -> discord.Embed:
    """
    Genera el embed de éxito para acciones de moderación, 
    soportando mensajes personalizados de la base de datos.
    """
    # Mapeo de claves de configuración y textos según la acción
    action_map = {
        "kick": {
            "config_key": "server_kick_msg",
            "title_key": "mod_title_kick",
            "default_title": "kick_title",
            "default_desc": "kick_desc"
        },
        "ban": {
            "config_key": "server_ban_msg",
            "title_key": "mod_title_ban",
            "default_title": "ban_title",
            "default_desc": "ban_desc"
        }
    }

    data = action_map.get(action)
    if not data:
        # Fallback genérico localizado
        title = lang_service.get_text("title_success", lang)
        desc = f"Acción {action} completada para **{user_name}**."
        return embed_service.success(title, desc)

    msg_custom = config.get(data["config_key"])

    if msg_custom:
        # Reemplazo de placeholders en mensaje personalizado
        desc = msg_custom.replace("{user}", user_name).replace("{reason}", reason)
        title = lang_service.get_text(data["title_key"], lang)
    else:
        # Mensaje por defecto del sistema de idiomas
        title = lang_service.get_text(data["default_title"], lang)
        desc = lang_service.get_text(data["default_desc"], lang, user=user_name, reason=reason)

    return embed_service.success(title, desc)

def get_clear_embed(count: int, lang: str) -> discord.Embed:
    title = lang_service.get_text("clear_success", lang)
    desc = lang_service.get_text("clear_desc", lang, count=count)
    return embed_service.success(title, desc, lite=True)

def get_timeout_embed(user_name: str, time_str: str, reason: str, lang: str) -> discord.Embed:
    title = lang_service.get_text("title_success", lang)
    msg = lang_service.get_text("timeout_success", lang, user=user_name, time=time_str, reason=reason)
    return embed_service.success(title, msg)

def get_untimeout_embed(user_name: str, lang: str) -> discord.Embed:
    title = lang_service.get_text("title_success", lang)
    msg = lang_service.get_text("untimeout_success", lang, user=user_name)
    return embed_service.success(title, msg, lite=True)

def get_warn_success_embed(user_name: str, count: int, reason: str, lang: str) -> discord.Embed:
    title = lang_service.get_text("title_success", lang)
    msg = lang_service.get_text("warn_success", lang, user=user_name, count=count, reason=reason)
    return embed_service.success(title, msg)

def get_clear_warns_embed(user_name: str, lang: str) -> discord.Embed:
    title = lang_service.get_text("title_success", lang)
    msg = lang_service.get_text("warn_cleared", lang, user=user_name)
    return embed_service.success(title, msg, lite=True)

def get_delwarn_success_embed(warn_id: int, lang: str) -> discord.Embed:
    title = lang_service.get_text("title_success", lang)
    msg = lang_service.get_text("warn_deleted", lang, id=warn_id)
    return embed_service.success(title, msg, lite=True)

def get_warns_pages(guild: discord.Guild, user_name: str, warns: list, lang: str) -> list[discord.Embed]:
    """Genera las páginas de embeds para el historial de advertencias."""
    chunk_size = settings.CONFIG.get("moderation_config", {}).get("warns_page_size", 5)
    chunks = [warns[i:i + chunk_size] for i in range(0, len(warns), chunk_size)]
    pages = []
    title = lang_service.get_text("warn_list_title", lang, user=user_name)

    for i, chunk in enumerate(chunks):
        desc = ""
        for w in chunk:
            # Convertir string de DB a timestamp de Discord
            dt = datetime.datetime.strptime(w['timestamp'], "%Y-%m-%d %H:%M:%S").replace(tzinfo=datetime.timezone.utc)
            ts = int(dt.timestamp())
            desc += f"`ID: {w['id']}` | <@{w['mod_id']}>: {w['reason']} (<t:{ts}:R>)\n\n"
        
        embed = discord.Embed(title=title, description=desc.strip(), color=settings.COLORS["WARNING"])
        if len(chunks) > 1:
            # Usamos el formato de página de leaderboard para consistencia
            footer_text = lang_service.get_text("leaderboard_footer", lang, current=i+1, total=len(chunks))
            embed.set_footer(text=footer_text)
        pages.append(embed)
    return pages