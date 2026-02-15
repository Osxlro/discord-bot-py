import discord
from discord import app_commands
from discord.ext import commands
from typing import Literal
from services.features import setup_service
from services.core import db_service, lang_service
from services.utils import embed_service

class Configuracion(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # --- HELPER INTERNO ---
    async def _apply_setup(self, ctx, updates: dict, label: str, value_display: str):
        """Aplica cambios de configuración usando el servicio y responde."""
        await ctx.defer(ephemeral=True)
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        embed = await setup_service.update_guild_setup(ctx.guild.id, updates, lang, label, value_display)
        await ctx.send(embed=embed, ephemeral=True)

    # ==========================================
    #             GRUPO PRINCIPAL: SETUP
    # ==========================================
    @commands.hybrid_group(name="setup", description="Panel de configuración del servidor.")
    @commands.has_permissions(administrator=True)
    async def setup(self, ctx: commands.Context):
        """Comando base para la configuración. Si se usa solo, muestra la ayuda."""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @setup.command(name="info", description="Muestra un resumen de la configuración del servidor.")
    async def info(self, ctx: commands.Context):
        """Muestra un resumen detallado de la configuración actual del bot en el servidor."""
        await ctx.defer(ephemeral=True)
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        embed = await setup_service.get_setup_info_embed(ctx.guild, lang)
        await ctx.send(embed=embed, ephemeral=True)

    # --- SECCIÓN: CONFIGURACIÓN DE CANALES ---

    @setup.command(name="welcome", description="Establece el canal de bienvenidas.")
    @app_commands.describe(canal="Canal donde se enviarán las bienvenidas")
    async def bienvenida(self, ctx: commands.Context, canal: discord.TextChannel):
        await self._apply_setup(ctx, {"welcome_channel_id": canal.id}, "Bienvenida", canal.mention)

    @setup.command(name="confess", description="Establece el canal de confesiones anónimas.")
    @app_commands.describe(canal="Canal para las confesiones")
    async def confesiones(self, ctx: commands.Context, canal: discord.TextChannel):
        await self._apply_setup(ctx, {"confessions_channel_id": canal.id}, "Confesiones", canal.mention)

    @setup.command(name="logs", description="Establece el canal de registros (logs).")
    @app_commands.describe(canal="Canal para logs de moderación")
    async def logs(self, ctx: commands.Context, canal: discord.TextChannel):
        await self._apply_setup(ctx, {"logs_channel_id": canal.id}, "Logs", canal.mention)

    @setup.command(name="birthday", description="Establece el canal de avisos de cumpleaños.")
    @app_commands.describe(canal="Canal para felicitaciones")
    async def cumpleanos(self, ctx: commands.Context, canal: discord.TextChannel):
        await self._apply_setup(ctx, {"birthday_channel_id": canal.id}, "Cumpleaños", canal.mention)

    # --- SECCIÓN: AJUSTES DE COMPORTAMIENTO Y MENSAJES ---

    @setup.command(name="goodbye", description="Personaliza el mensaje de despedida.")
    @app_commands.describe(mensaje="Usa {user} para el nombre y {server} para el servidor. Escribe 'reset' para borrar.")
    async def goodbye(self, ctx: commands.Context, mensaje: str):
        """Actualiza el mensaje de despedida o lo resetea a NULL."""
        val = None if mensaje.lower() == "reset" else mensaje
        await self._apply_setup(ctx, {"server_goodbye_msg": val}, "Despedida", "✅ Actualizado" if val else "❌ Reseteado")

    @setup.command(name="lang", description="Cambia el idioma del bot en este servidor.")
    @app_commands.describe(opcion="Selecciona el idioma (Español/English)")
    async def lang(self, ctx: commands.Context, opcion: Literal["es", "en"]):
        """Cambia el idioma de respuesta del bot para el servidor actual."""
        display = "Español 🇪🇸" if opcion == "es" else "English 🇺🇸"
        await self._apply_setup(ctx, {"language": opcion}, "Idioma", display)

    @setup.command(name="chaos", description="Configura el sistema Chaos (ruleta rusa).")
    @app_commands.describe(
        estado="Activar o desactivar el sistema",
        probabilidad="Probabilidad de activación (ej: 1 para 1%)"
    )
    async def chaos(self, ctx: commands.Context, estado: bool, probabilidad: float):
        """Configura la probabilidad y estado del sistema Chaos."""
        # Normalizar probabilidad (0.1% a 100%) y convertir a decimal para la DB
        prob_clamped = max(0.1, min(100.0, probabilidad))
        prob_decimal = prob_clamped / 100.0
        status_txt = "✅ Activado" if estado else "❌ Desactivado"

        await self._apply_setup(ctx, {"chaos_enabled": 1 if estado else 0, "chaos_probability": prob_decimal}, "Chaos", f"{status_txt} ({prob_clamped}%)")
        
        # Sincronizar con la caché del evento Chaos si el Cog está cargado
        chaos_cog = self.bot.get_cog("Chaos")
        if chaos_cog:
            chaos_cog.update_local_config(ctx.guild.id, estado, prob_decimal)

    # ==========================================
    #           SUBGRUPO: WORDDAY (Frase del Día)
    # ==========================================
    @setup.group(name="wordday", description="Configura la frase del día.")
    async def wordday_group(self, ctx: commands.Context):
        """Subgrupo para gestionar el sistema de frases diarias."""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @wordday_group.command(name="channel", description="Establece el canal para la frase del día.")
    @app_commands.describe(canal="Canal donde se enviará la frase")
    async def wordday_channel(self, ctx: commands.Context, canal: discord.TextChannel):
        await self._apply_setup(ctx, {"wordday_channel_id": canal.id}, "Frase del Día", canal.mention)

    @wordday_group.command(name="role", description="Establece el rol a mencionar.")
    @app_commands.describe(rol="Rol a mencionar")
    async def wordday_role(self, ctx: commands.Context, rol: discord.Role):
        await self._apply_setup(ctx, {"wordday_role_id": rol.id}, "Rol Frase del Día", rol.mention)

async def setup(bot):
    await bot.add_cog(Configuracion(bot))