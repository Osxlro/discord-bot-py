import discord
import datetime
from config import settings

def _base_embed(title: str, description: str, color: int) -> discord.Embed:
    """Constructor base para todos los embeds."""
    embed = discord.Embed(
        title=title,
        description=description,
        color=color,
        timestamp=datetime.datetime.now()
    )
    # Pie de página por defecto con el nombre del bot (opcional)
    # embed.set_footer(text="Oscurin Inc") 
    return embed

def success(title: str, description: str, lite: bool = False) -> discord.Embed:
    """Embed Verde para acciones exitosas."""
    embed = _base_embed(title, description, settings.COLORS["SUCCESS"])
    if not lite:
        embed.set_thumbnail(url=settings.get_bot_icon())
    return embed

def error(title: str, description: str) -> discord.Embed:
    """Embed Rojo para errores."""
    embed = _base_embed(title, description, settings.COLORS["ERROR"])
    return embed

def info(title: str, description: str, thumbnail: str = None) -> discord.Embed:
    """Embed Azul para información general."""
    embed = _base_embed(title, description, settings.COLORS["INFO"])
    if thumbnail:
        embed.set_thumbnail(url=thumbnail)
    return embed

def warning(title: str, description: str) -> discord.Embed:
    """Embed Amarillo para advertencias."""
    embed = _base_embed(title, description, settings.COLORS["WARNING"])
    return embed

def xp_embed(title: str, description: str) -> discord.Embed:
    """Embed Violeta especial para niveles."""
    embed = _base_embed(title, description, settings.COLORS["XP"])
    return embed