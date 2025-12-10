# Archivo: cogs/general.py
import discord
from discord.ext import commands
from discord import app_commands
from services import math_service, embed_service

class General(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="hola", description="Te da la bienvenida")
    async def hola(self, interaction: discord.Interaction):
        saludo = math_service.obtener_saludo_personalizado(interaction.user.name)
        embed = embed_service.info("Bienvenida", saludo)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="ping", description="Muestra la latencia del bot")
    async def ping(self, interaction: discord.Interaction):
        latencia = round(self.bot.latency * 1000)
        embed = embed_service.info("Ping", f"🏓 Pong! Latencia: **{latencia}ms**")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="avatar", description="Muestra el avatar de un usuario")
    async def avatar(self, interaction: discord.Interaction, usuario: discord.Member = None):
        # Si no especifica usuario, usa el suyo propio
        usuario = usuario or interaction.user
        
        embed = embed_service.info(f"Avatar de {usuario.name}", "")
        embed.set_image(url=usuario.display_avatar.url)
        
        await interaction.response.send_message(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(General(bot))