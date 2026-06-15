import discord
from services.core import db_service
from ui import setup_ui

async def handle_setup_update(guild_id: int, updates: dict, lang: str, label: str, value_display: str) -> discord.Embed:
    """Actualiza la configuración y delega el embed de éxito a la UI."""
    await db_service.update_guild_config(guild_id, updates)
    return setup_ui.get_setup_success_embed(lang, label, value_display)

async def handle_chaos_setup(bot, guild_id: int, estado: bool, probabilidad: float = None, lang: str = "es") -> discord.Embed:
    """Maneja la lógica específica de Chaos y retorna el embed de la UI."""
    config = await db_service.get_guild_config(guild_id)
    
    updates = {}
    if estado is not None:
        updates["chaos_enabled"] = 1 if estado else 0
    
    if probabilidad is not None:
        # Normalizar probabilidad (0.1% a 100%) y convertir a decimal para la DB
        prob_clamped = max(0.1, min(100.0, probabilidad))
        prob_decimal = prob_clamped / 100.0
        updates["chaos_probability"] = prob_decimal
    else:
        prob_decimal = config.get("chaos_probability", 0.01)
        prob_clamped = prob_decimal * 100
        
    if updates:
        await db_service.update_guild_config(guild_id, updates)
        
    # Sincronizar con el Cog de Chaos si está cargado
    chaos_cog = bot.get_cog("Chaos")
    if chaos_cog:
        current_enabled = updates.get("chaos_enabled", config.get("chaos_enabled", 1))
        chaos_cog.update_local_config(guild_id, bool(current_enabled), prob_decimal)
        
    status_txt = "✅" if updates.get("chaos_enabled", config.get("chaos_enabled", 1)) else "❌"
    value_display = f"{status_txt} ({prob_clamped:.1f}%)"
    
    return setup_ui.get_setup_success_embed(lang, "Chaos", value_display)