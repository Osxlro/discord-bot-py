import discord
from discord import app_commands
from discord.ext import commands
from typing import Literal
from services.features import setup_service
from services.core import lang_service

class Configuracion(commands.Cog):
    """
    Cog encargado de la gestión de ajustes del servidor.
    Permite a los administradores configurar canales, idiomas y sistemas especiales.
    """
    def __init__(self, bot):
        self.bot = bot

    # --- HELPER INTERNO ---
    async def _apply_setup(self, ctx, updates: dict, label: str, value_display: str):
        """
        Método auxiliar para procesar actualizaciones de configuración.
        Centraliza la llamada al servicio, la obtención del idioma y la respuesta al usuario.
        """
        await ctx.defer(ephemeral=True)
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        embed = await setup_service.handle_setup_update(ctx.guild.id, updates, lang, label, value_display)
        await ctx.send(embed=embed, ephemeral=True)

    # ==========================================
    #             GRUPO PRINCIPAL: SETUP
    # ==========================================
    @commands.hybrid_group(name="setup", description="Panel de configuración del servidor.")
    @commands.has_permissions(administrator=True)
    async def setup(self, ctx: commands.Context):
        """
        Comando base del grupo 'setup'. 
        Si no se especifica un subcomando, muestra el menú de ayuda del grupo.
        """
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @setup.command(name="info", description="Muestra un resumen de la configuración del servidor.")
    async def info(self, ctx: commands.Context):
        """
        Muestra un panel informativo con todos los ajustes actuales aplicados en el servidor.
        """
        await ctx.defer(ephemeral=True)
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        embed = await setup_service.handle_get_info(ctx.guild, lang)
        await ctx.send(embed=embed, ephemeral=True)

    # --- SECCIÓN: CONFIGURACIÓN DE CANALES ---

    @setup.command(name="welcome", description="Establece el canal de bienvenidas.")
    @app_commands.describe(canal="Canal donde se enviarán las bienvenidas (deja vacío para desactivar)")
    async def bienvenida(self, ctx: commands.Context, canal: discord.TextChannel = None):
        """Configura el canal donde el bot enviará los mensajes de bienvenida."""
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        val = canal.id if canal else 0
        display = canal.mention if canal else lang_service.get_text("setup_disabled", lang)
        await self._apply_setup(ctx, {"welcome_channel_id": val}, lang_service.get_text("sim_welcome", lang), display)

    @setup.command(name="confess", description="Establece el canal de confesiones anónimas.")
    @app_commands.describe(canal="Canal para las confesiones (deja vacío para desactivar)")
    async def confesiones(self, ctx: commands.Context, canal: discord.TextChannel = None):
        """Configura el canal destinado a recibir las confesiones anónimas de los usuarios."""
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        val = canal.id if canal else 0
        display = canal.mention if canal else lang_service.get_text("setup_disabled", lang)
        await self._apply_setup(ctx, {"confessions_channel_id": val}, lang_service.get_text("confess_title", lang), display)

    @setup.command(name="logs", description="Establece el canal de registros (logs).")
    @app_commands.describe(canal="Canal para logs de moderación (deja vacío para desactivar)")
    async def logs(self, ctx: commands.Context, canal: discord.TextChannel = None):
        """Configura el canal donde se registrarán las acciones de moderación y eventos del servidor."""
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        val = canal.id if canal else 0
        display = canal.mention if canal else lang_service.get_text("setup_disabled", lang)
        await self._apply_setup(ctx, {"logs_channel_id": val}, lang_service.get_text("setup_logs_label", lang), display)

    @setup.command(name="birthday", description="Establece el canal de avisos de cumpleaños.")
    @app_commands.describe(canal="Canal para felicitaciones (deja vacío para desactivar)")
    async def cumpleanos(self, ctx: commands.Context, canal: discord.TextChannel = None):
        """Configura el canal donde el bot anunciará automáticamente los cumpleaños."""
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        val = canal.id if canal else 0
        display = canal.mention if canal else lang_service.get_text("setup_disabled", lang)
        await self._apply_setup(ctx, {"birthday_channel_id": val}, lang_service.get_text("sim_birthday", lang), display)

    # --- SECCIÓN: AJUSTES DE COMPORTAMIENTO Y MENSAJES ---

    @setup.command(name="goodbye", description="Personaliza el mensaje de despedida.")
    @app_commands.describe(mensaje="Usa {user} para el nombre y {server} para el servidor. Deja vacío o escribe 'reset' para desactivar.")
    async def goodbye(self, ctx: commands.Context, mensaje: str = None):
        """
        Establece un mensaje personalizado para cuando un usuario abandona el servidor.
        Permite el uso de variables dinámicas como {user} y {server}.
        """
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        val = None if not mensaje or mensaje.lower() == "reset" else mensaje
        display = val if val else lang_service.get_text("setup_disabled", lang)
        await self._apply_setup(ctx, {"server_goodbye_msg": val}, lang_service.get_text("goodbye_title", lang), display)

    @setup.command(name="lang", description="Cambia el idioma del bot en este servidor.")
    @app_commands.describe(opcion="Selecciona el idioma (Español/English/Português/Français)")
    async def lang(self, ctx: commands.Context, opcion: Literal["es", "en", "pt", "fr"]):
        """
        Cambia el idioma global en el que el bot responderá dentro del servidor actual.
        """
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        display_map = {"es": "Español 🇪🇸", "en": "English 🇺🇸", "pt": "Português 🇵🇹", "fr": "Français 🇫🇷"}
        display = display_map.get(opcion, "Unknown")
        await self._apply_setup(ctx, {"language": opcion}, lang_service.get_text("botinfo_langs", lang), display)

    @setup.command(name="chaos", description="Configura el sistema Chaos (ruleta rusa).")
    @app_commands.describe(
        estado="Activar o desactivar el sistema",
        probabilidad="Probabilidad de activación (0.1 a 100)"
    )
    async def chaos(self, ctx: commands.Context, estado: bool, probabilidad: float):
        """
        Configura el sistema Chaos (ruleta rusa de mensajes).
        Permite activar/desactivar el sistema y ajustar la probabilidad de que un usuario sea aislado.
        """
        embed = await setup_service.handle_chaos_setup(self.bot, ctx.guild.id, estado, probabilidad, await lang_service.get_guild_lang(ctx.guild.id))
        await ctx.send(embed=embed, ephemeral=True)

    @setup.command(name="autorole", description="Establece el rol que se asignará automáticamente a los nuevos miembros.")
    @app_commands.describe(rol="Rol a asignar (deja vacío para desactivar)")
    async def autorole(self, ctx: commands.Context, rol: discord.Role = None):
        """Configura el rol que el bot asignará automáticamente a los nuevos miembros al unirse."""
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        val = rol.id if rol else 0
        display = rol.mention if rol else lang_service.get_text("setup_disabled", lang)
        await self._apply_setup(ctx, {"autorole_id": val}, lang_service.get_text("setup_autorol_label", lang), display)

    # ==========================================
    #           SUBGRUPO: WORDDAY (Frase del Día)
    # ==========================================
    @setup.group(name="wordday", description="Configura la frase del día.")
    async def wordday_group(self, ctx: commands.Context):
        """Subgrupo de comandos para gestionar el sistema de envío de frases inspiracionales diarias."""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @wordday_group.command(name="channel", description="Establece el canal para la frase del día.")
    @app_commands.describe(canal="Canal donde se enviará la frase (deja vacío para desactivar)")
    async def wordday_channel(self, ctx: commands.Context, canal: discord.TextChannel = None):
        """Configura el canal donde se publicará la frase del día cada mañana."""
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        val = canal.id if canal else 0
        display = canal.mention if canal else lang_service.get_text("setup_disabled", lang)
        await self._apply_setup(ctx, {"wordday_channel_id": val}, lang_service.get_text("wordday_title", lang), display)

    @wordday_group.command(name="role", description="Establece el rol a mencionar.")
    @app_commands.describe(rol="Rol a mencionar (deja vacío para desactivar)")
    async def wordday_role(self, ctx: commands.Context, rol: discord.Role = None):
        """Configura el rol que el bot mencionará al publicar la frase del día."""
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        val = rol.id if rol else 0
        display = rol.mention if rol else lang_service.get_text("setup_disabled", lang)
        await self._apply_setup(ctx, {"wordday_role_id": val}, lang_service.get_text("setup_wordday_role_label", lang), display)

async def setup(bot):
    await bot.add_cog(Configuracion(bot))