import discord
import datetime
from config import settings

def _get_base_embed(title: str, description: str, color_key: str) -> discord.Embed:
    """Función interna para construir el embed base con footer y timestamp."""
    
    # Obtenemos el color desde settings (que lee config.json)
    # settings.get_color ya lo implementamos en el paso anterior
    color = settings.get_color(color_key)
    
    embed = discord.Embed(
        title=title,
        description=description,
        color=color,
        timestamp=datetime.datetime.now()
    )
    # Footer genérico para marca de agua
    embed.set_footer(text=f"{settings.CONFIG['bot_config']['description']} • v{settings.CONFIG['bot_config']['version']}")
    return embed

def success(title: str, description: str) -> discord.Embed:
    """Genera un embed verde de éxito."""
    return _get_base_embed(f"✅ {title}", description, "success")

def error(title: str, description: str) -> discord.Embed:
    """Genera un embed rojo de error."""
    return _get_base_embed(f"⛔ {title}", description, "error")

def info(title: str, description: str) -> discord.Embed:
    """Genera un embed azul de información."""
    return _get_base_embed(f"ℹ️ {title}", description, "info")