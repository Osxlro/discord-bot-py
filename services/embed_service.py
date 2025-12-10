import discord
import datetime
from config import settings

# 1. Añadimos el argumento opcional icon_url=None
def _get_base_embed(title: str, description: str, color_key: str, icon_url: str = None) -> discord.Embed:
    """Función interna para construir el embed base con footer y timestamp."""
    
    color = settings.get_color(color_key)
    
    embed = discord.Embed(
        title=title,
        description=description,
        color=color,
        timestamp=datetime.datetime.now()
    )
    
    # 2. Usamos icon_url en el footer si se proporciona
    footer_text = f"{settings.CONFIG['bot_config']['description']}  •  v{settings.CONFIG['bot_config']['version']}"
        # Imagen
    icon_url = settings.get_bot_icon()

    if icon_url:
        embed.set_footer(text=footer_text, icon_url=icon_url)
    else:
        embed.set_footer(text=footer_text)
        
    return embed

# 3. Actualizamos las funciones públicas para que acepten el parámetro
def success(title: str, description: str, icon_url: str = None) -> discord.Embed:
    return _get_base_embed(f"✅ {title}", description, "success", icon_url)

def error(title: str, description: str, icon_url: str = None) -> discord.Embed:
    return _get_base_embed(f"⛔ {title}", description, "error", icon_url)

def info(title: str, description: str, icon_url: str = None) -> discord.Embed:
    return _get_base_embed(f"ℹ️ {title}", description, "info", icon_url)