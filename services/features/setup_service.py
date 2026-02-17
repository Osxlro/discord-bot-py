import discord
from services.core import db_service
from ui import setup_ui

async def handle_get_info(guild: discord.Guild, lang: str) -> discord.Embed:
    """Obtiene la configuración y delega la creación del embed a la UI."""
    config = await db_service.get_guild_config(guild.id)
    return setup_ui.get_setup_info_embed(guild, config, lang)

async def handle_setup_update(guild_id: int, updates: dict, lang: str, label: str, value_display: str) -> discord.Embed:
    """Actualiza la configuración y delega el embed de éxito a la UI."""
    await db_service.update_guild_config(guild_id, updates)
    return setup_ui.get_setup_success_embed(lang, label, value_display)

async def handle_chaos_setup(bot, guild_id: int, estado: bool, probabilidad: float, lang: str) -> discord.Embed:
    """Maneja la lógica específica de Chaos y retorna el embed de la UI."""
    # Normalizar probabilidad (0.1% a 100%) y convertir a decimal para la DB
    prob_clamped = max(0.1, min(100.0, probabilidad))
    prob_decimal = prob_clamped / 100.0
    
    updates = {
        "chaos_enabled": 1 if estado else 0,
        "chaos_probability": prob_decimal
    }
    await db_service.update_guild_config(guild_id, updates)
    
    # Sincronizar con el Cog de Chaos si está cargado
    chaos_cog = bot.get_cog("Chaos")
    if chaos_cog:
        chaos_cog.update_local_config(guild_id, estado, prob_decimal)
        
    status_txt = "✅" if estado else "❌"
    value_display = f"{status_txt} ({prob_clamped}%)"
    
    return setup_ui.get_setup_success_embed(lang, "Chaos", value_display)