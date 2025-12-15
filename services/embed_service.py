import discord
import datetime
from config import settings

def _get_base_embed(title: str, description: str, color_key: str, thumbnail: str = None, image: str = None, footer: str = None, lite: bool = False) -> discord.Embed:
    color = settings.get_color(color_key)
    
    embed = discord.Embed(
        title=title,
        description=description,
        color=color
    )
    
    # 1. Thumbnail integrado
    if thumbnail:
        embed.set_thumbnail(url=thumbnail)
    
    # 2. Imagen grande integrada
    if image:
        embed.set_image(url=image)

    # 3. Lógica de Footer
    if not lite:
        embed.timestamp = datetime.datetime.now()
        # Si pasan un footer personalizado, se usa. Si no, el default.
        text_footer = footer if footer else f"{settings.CONFIG['bot_config']['description']} • v{settings.CONFIG['bot_config']['version']}"
        icon_footer = settings.get_bot_icon()
        
        if icon_footer:
            embed.set_footer(text=text_footer, icon_url=icon_footer)
        else:
            embed.set_footer(text=text_footer)
    elif footer:
        # Si es lite pero especificaron footer (ej: confesiones)
        embed.set_footer(text=footer)
        
    return embed

# Funciones públicas con los nuevos argumentos
def success(title: str, description: str, thumbnail: str = None, image: str = None, footer: str = None, lite: bool = False) -> discord.Embed:
    return _get_base_embed(f"✅ {title}", description, "success", thumbnail, image, footer, lite)

def error(title: str, description: str, thumbnail: str = None, image: str = None, footer: str = None, lite: bool = False) -> discord.Embed:
    return _get_base_embed(f"⛔ {title}", description, "error", thumbnail, image, footer, lite)

def info(title: str, description: str, thumbnail: str = None, image: str = None, footer: str = None, lite: bool = False) -> discord.Embed:
    titulo_fmt = f"ℹ️ {title}" if not lite else title
    return _get_base_embed(titulo_fmt, description, "info", thumbnail, image, footer, lite)