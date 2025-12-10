# Archivo: cogs/general.py
import discord
from discord.ext import commands
from discord import app_commands
from services import math_service, embed_service

class General(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_command(name="ping", description="Muestra la latencia del bot")
    async def ping(self, ctx: commands.Context):
        latencia = round(self.bot.latency * 1000)
        embed = embed_service.info("Ping", f"🏓 Pong! Latencia: **{latencia}ms**")
        await ctx.reply(embed=embed)

    @commands.hybrid_command(name="avatar", description="Muestra el avatar de un usuario")
    async def avatar(self, ctx: commands.Context, usuario: discord.Member = None):
        # Si no especifica usuario, usa el suyo propio
        usuario = usuario or interaction.user
        
        embed = embed_service.info(f"Avatar de {usuario.name}", "")
        embed.set_image(url=usuario.display_avatar.url)
        
        await ctx.reply(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(General(bot))