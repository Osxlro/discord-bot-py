import discord
from ui import help_ui
from services.core import lang_service

# Re-exportamos para mantener compatibilidad con cualquier módulo que aún use help_service
__all__ = ["get_help_options", "get_home_embed", "get_module_embed", "handle_help"]

async def handle_help(bot: discord.Client, ctx, lang: str):
    embed = await help_ui.get_home_embed(bot, ctx.guild, ctx.author, lang)
    view = help_ui.HelpView(bot, ctx, lang)
    return embed, view