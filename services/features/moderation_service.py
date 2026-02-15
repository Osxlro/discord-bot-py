import re
import discord
from services.utils import embed_service
from services.core import lang_service

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
        return embed_service.success("Moderación", f"Acción {action} completada.")

    msg_custom = config.get(data["config_key"])

    if msg_custom:
        # Reemplazo de placeholders
        desc = msg_custom.replace("{user}", user_name).replace("{reason}", reason)
        title = lang_service.get_text(data["title_key"], lang)
    else:
        # Mensaje por defecto del sistema de idiomas
        title = lang_service.get_text(data["default_title"], lang)
        desc = lang_service.get_text(data["default_desc"], lang, user=user_name, reason=reason)

    return embed_service.success(title, desc)