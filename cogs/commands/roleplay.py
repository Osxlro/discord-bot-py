import discord
from discord.ext import commands
from discord import app_commands
from services.core import lang_service
from services.utils import embed_service

class Roleplay(commands.Cog):
    """
    Cog de interacciones y juegos de rol (Roleplay).
    Permite interacciones de usuarios (/kiss, /hug, etc.).
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # Módulo de Roleplay inicializado de forma preliminar.
    # Aquí se definirán los comandos (/kiss, /hug, etc.) una vez elegida la API correspondiente.

async def setup(bot: commands.Bot):
    await bot.add_cog(Roleplay(bot))
