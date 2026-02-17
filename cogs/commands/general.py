import discord
import logging
from discord import app_commands
from discord.ext import commands
from config.locales import LOCALES
from services.features import general_service, help_service
from services.core import lang_service
from services.utils import embed_service

logger = logging.getLogger(__name__)

class General(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Nota: El nombre del menú contextual se define en español por defecto o desde locales
        self.ctx_menu = app_commands.ContextMenu(name=LOCALES["es"]["ctx_menu_translate"], callback=self.traducir_mensaje)
        self.bot.tree.add_command(self.ctx_menu)

    async def cog_unload(self):
        self.bot.tree.remove_command(self.ctx_menu.name, type=self.ctx_menu.type)

    @commands.hybrid_command(name="help", description="Muestra el panel de ayuda y comandos.")
    async def help(self, ctx: commands.Context):
        lang = await lang_service.get_guild_lang(ctx.guild.id if ctx.guild else None)
        embed, view = await help_service.handle_help(self.bot, ctx, lang)
        await ctx.send(embed=embed, view=view)

    @commands.hybrid_command(name="ping", description="Muestra la latencia actual del bot.")
    async def ping(self, ctx: commands.Context):
        lang = await lang_service.get_guild_lang(ctx.guild.id if ctx.guild else None)
        embed = await general_service.handle_ping(self.bot, lang)
        await ctx.reply(embed=embed)

    @commands.hybrid_command(name="calc", description="Calculadora flexible. Ej: /calc + 5 10")
    @app_commands.describe(operacion="Usa símbolos (+, -, *, /)", num1="Primer número", num2="Segundo número")
    async def calc(self, ctx: commands.Context, operacion: str, num1: float, num2: float):
        lang = await lang_service.get_guild_lang(ctx.guild.id if ctx.guild else None)
        embed, error = await general_service.handle_calc(operacion, num1, num2, lang)
        if error:
            return await ctx.reply(embed=embed_service.error(lang_service.get_text("title_error", lang), error, lite=True), ephemeral=True)
        await ctx.reply(embed=embed)

    @commands.hybrid_command(name="serverinfo", description="Muestra información y configuración del servidor.")
    @commands.guild_only()
    async def serverinfo(self, ctx: commands.Context):
        await ctx.defer()
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        embed = await general_service.handle_serverinfo(ctx.guild, lang)
        await ctx.send(embed=embed)

    async def traducir_mensaje(self, interaction: discord.Interaction, message: discord.Message):
        lang = await lang_service.get_guild_lang(interaction.guild_id)
        await interaction.response.defer(ephemeral=True)
        embed, error = await general_service.handle_translate(message.content, lang)
        if error:
            return await interaction.followup.send(embed=embed_service.error(lang_service.get_text("title_error", lang), error, lite=True), ephemeral=True)
        await interaction.followup.send(embed=embed, ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(General(bot))