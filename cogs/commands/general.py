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
    """
    Cog de comandos generales y de utilidad.
    Incluye funciones básicas como ayuda, ping, calculadora e información del servidor.
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Inicialización del menú contextual para traducción de mensajes.
        # Se registra en el árbol de comandos de la aplicación.
        self.ctx_menu = app_commands.ContextMenu(name=LOCALES["es"]["ctx_menu_translate"], callback=self.traducir_mensaje)
        self.bot.tree.add_command(self.ctx_menu)

    async def cog_unload(self):
        """Limpieza al descargar el Cog: elimina el menú contextual del árbol de comandos."""
        self.bot.tree.remove_command(self.ctx_menu.name, type=self.ctx_menu.type)

    @commands.hybrid_command(name="help", description="Muestra el panel de ayuda y comandos.")
    async def help(self, ctx: commands.Context):
        """Muestra un panel interactivo con la lista de comandos disponibles."""
        lang = await lang_service.get_guild_lang(ctx.guild.id if ctx.guild else None)
        # Delegamos la orquestación de la ayuda al servicio especializado
        embed, view = await help_service.handle_help(self.bot, ctx, lang)
        await ctx.send(embed=embed, view=view)

    @commands.hybrid_command(name="ping", description="Muestra la latencia actual del bot.")
    async def ping(self, ctx: commands.Context):
        """Comando simple para verificar la respuesta y latencia del bot."""
        lang = await lang_service.get_guild_lang(ctx.guild.id if ctx.guild else None)
        # El servicio calcula la latencia y solicita el embed a la UI
        embed = await general_service.handle_ping(self.bot, lang)
        await ctx.reply(embed=embed)

    @commands.hybrid_command(name="calc", description="Calculadora flexible. Ej: /calc + 5 10")
    @app_commands.describe(operacion="Usa símbolos (+, -, *, /)", num1="Primer número", num2="Segundo número")
    async def calc(self, ctx: commands.Context, operacion: str, num1: float, num2: float):
        """Realiza operaciones matemáticas básicas procesadas por el servicio."""
        lang = await lang_service.get_guild_lang(ctx.guild.id if ctx.guild else None)
        # El servicio maneja la lógica matemática y validaciones (como división por cero)
        embed, error = await general_service.handle_calc(operacion, num1, num2, lang)
        if error:
            return await ctx.reply(embed=embed_service.error(lang_service.get_text("title_error", lang), error, lite=True), ephemeral=True)
        await ctx.reply(embed=embed)

    @commands.hybrid_command(name="serverinfo", description="Muestra información y configuración del servidor.")
    @commands.guild_only()
    async def serverinfo(self, ctx: commands.Context):
        """Muestra estadísticas detalladas y ajustes actuales del servidor."""
        await ctx.defer()
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        # El servicio recopila estadísticas del servidor y configuración de la base de datos
        embed = await general_service.handle_serverinfo(ctx.guild, lang)
        await ctx.send(embed=embed)

    async def traducir_mensaje(self, interaction: discord.Interaction, message: discord.Message):
        """
        Callback para el menú contextual de traducción.
        Traduce el contenido del mensaje seleccionado al idioma por defecto del bot.
        """
        lang = await lang_service.get_guild_lang(interaction.guild_id)
        await interaction.response.defer(ephemeral=True)
        # El servicio orquesta la integración con el traductor y la generación visual
        embed, error = await general_service.handle_translate(message.content, lang)
        if error:
            return await interaction.followup.send(embed=embed_service.error(lang_service.get_text("title_error", lang), error, lite=True), ephemeral=True)
        await interaction.followup.send(embed=embed, ephemeral=True)

async def setup(bot: commands.Bot):
    """Función de entrada para cargar el Cog en el bot."""
    await bot.add_cog(General(bot))