import discord
from discord import app_commands
from discord.ext import commands
from typing import Literal
from services import db_service, embed_service, lang_service

class Configuracion(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # --- HELPER INTERNO ---
    async def _update_channel_config(self, ctx, key: str, channel: discord.TextChannel, label: str):
        """Helper para actualizar configuraciones de canales repetitivas."""
        await ctx.defer(ephemeral=True)
        await db_service.update_guild_config(ctx.guild.id, {key: channel.id})
        
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        msg = lang_service.get_text("setup_desc", lang, type=label, value=channel.mention)
        await ctx.send(embed=embed_service.success(lang_service.get_text("setup_success", lang), msg), ephemeral=True)

    # --- GRUPO SETUP ---
    @commands.hybrid_group(name="setup", description="Panel de configuración del servidor.")
    @commands.has_permissions(administrator=True)
    async def setup(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @setup.command(name="bienvenida", description="Establece el canal de bienvenidas.")
    @app_commands.describe(canal="Canal donde se enviarán las bienvenidas")
    async def bienvenida(self, ctx: commands.Context, canal: discord.TextChannel):
        await self._update_channel_config(ctx, "welcome_channel_id", canal, "Bienvenida")

    @setup.command(name="confesiones", description="Establece el canal de confesiones anónimas.")
    @app_commands.describe(canal="Canal para las confesiones")
    async def confesiones(self, ctx: commands.Context, canal: discord.TextChannel):
        await self._update_channel_config(ctx, "confessions_channel_id", canal, "Confesiones")

    @setup.command(name="logs", description="Establece el canal de registros (logs).")
    @app_commands.describe(canal="Canal para logs de moderación")
    async def logs(self, ctx: commands.Context, canal: discord.TextChannel):
        await self._update_channel_config(ctx, "logs_channel_id", canal, "Logs")

    @setup.command(name="cumpleanos", description="Establece el canal de avisos de cumpleaños.")
    @app_commands.describe(canal="Canal para felicitaciones")
    async def cumpleanos(self, ctx: commands.Context, canal: discord.TextChannel):
        await self._update_channel_config(ctx, "birthday_channel_id", canal, "Cumpleaños")

    @setup.command(name="idioma", description="Cambia el idioma del bot en este servidor.")
    @app_commands.describe(opcion="Selecciona el idioma (Español/English)")
    async def idioma(self, ctx: commands.Context, opcion: Literal["es", "en"]):
        await ctx.defer(ephemeral=True)
        await db_service.update_guild_config(ctx.guild.id, {"language": opcion})
        
        # Usamos el idioma seleccionado para responder
        lang = opcion
        display = "Español 🇪🇸" if opcion == "es" else "English 🇺🇸"
        
        msg = lang_service.get_text("setup_desc", lang, type="Idioma", value=display)
        await ctx.send(embed=embed_service.success(lang_service.get_text("setup_success", lang), msg), ephemeral=True)

async def setup(bot):
    await bot.add_cog(Configuracion(bot))