import discord
import datetime
from config import settings

def _get_base_embed(title: str, description: str, color_key: str, icon_url: str = None, lite: bool = False) -> discord.Embed:
    """
    lite=True: Elimina timestamp, footer y versión para una estética más limpia.
    """
    color = settings.get_color(color_key)
    
    embed = discord.Embed(
        title=title,
        description=description,
        color=color
    )
    
    if not lite:
        embed.timestamp = datetime.datetime.now()
        footer_text = f"{settings.CONFIG['bot_config']['description']} • v{settings.CONFIG['bot_config']['version']}"
        icon_url = settings.get_bot_icon()
        
        if icon_url:
            embed.set_footer(text=footer_text, icon_url=icon_url)
        else:
            embed.set_footer(text=footer_text)
        
    return embed

# Actualizamos las funciones públicas
def success(title: str, description: str, icon_url: str = None, lite: bool = False) -> discord.Embed:
    return _get_base_embed(f"✅ {title}", description, "success", icon_url, lite)

def error(title: str, description: str, icon_url: str = None, lite: bool = False) -> discord.Embed:
    return _get_base_embed(f"⛔ {title}", description, "error", icon_url, lite)

def info(title: str, description: str, icon_url: str = None, lite: bool = False) -> discord.Embed:
    # Para info, a veces no queremos el emoji en el título si es muy formal
    titulo_fmt = f"ℹ️ {title}" if not lite else title
    return _get_base_embed(titulo_fmt, description, "info", icon_url, lite)