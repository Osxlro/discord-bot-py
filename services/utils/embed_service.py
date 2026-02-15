import discord
import datetime
from config import settings

def _base_embed(title: str, description: str, color: int, footer: str = None, url: str = None) -> discord.Embed:
    """Constructor base para todos los embeds."""
    embed = discord.Embed(
        title=title,
        description=description,
        color=color,
        url=url,
        timestamp=datetime.datetime.now()
    )
    if footer:
        embed.set_footer(text=footer)
    return embed

def success(title: str, description: str, lite: bool = False, thumbnail: str = None, image: str = None, footer: str = None, url: str = None) -> discord.Embed:
    """Embed Verde para acciones exitosas."""
    embed = _base_embed(title, description, settings.COLORS["SUCCESS"], footer, url)
    
    # Lógica inteligente: Si das thumbnail manual, úsalo. Si no, y no es lite, usa el del bot.
    if thumbnail:
        embed.set_thumbnail(url=thumbnail)
    elif not lite:
        embed.set_thumbnail(url=settings.get_bot_icon())
        
    if image:
        embed.set_image(url=image)
    return embed

def error(title: str, description: str, lite: bool = False, thumbnail: str = None, image: str = None, footer: str = None, url: str = None) -> discord.Embed:
    """Embed Rojo para errores."""
    embed = _base_embed(title, description, settings.COLORS["ERROR"], footer, url)
    if thumbnail:
        embed.set_thumbnail(url=thumbnail)
    if image:
        embed.set_image(url=image)
    return embed

def info(title: str, description: str, thumbnail: str = None, image: str = None, lite: bool = False, footer: str = None, url: str = None) -> discord.Embed:
    """Embed Azul para información general."""
    embed = _base_embed(title, description, settings.COLORS["INFO"], footer, url)
    if thumbnail:
        embed.set_thumbnail(url=thumbnail)
    if image:
        embed.set_image(url=image)
    return embed

def warning(title: str, description: str, lite: bool = False, thumbnail: str = None, image: str = None, footer: str = None, url: str = None) -> discord.Embed:
    """Embed Amarillo para advertencias."""
    embed = _base_embed(title, description, settings.COLORS["WARNING"], footer, url)
    if thumbnail:
        embed.set_thumbnail(url=thumbnail)
    if image:
        embed.set_image(url=image)
    return embed

def xp_embed(title: str, description: str, thumbnail: str = None, image: str = None, footer: str = None, url: str = None) -> discord.Embed:
    """Embed Violeta especial para niveles."""
    embed = _base_embed(title, description, settings.COLORS["XP"], footer, url)
    if thumbnail:
        embed.set_thumbnail(url=thumbnail)
    if image:
        embed.set_image(url=image)
    return embed