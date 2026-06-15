import discord
from discord import app_commands
from discord.ext import commands
from typing import Literal
from services.features import setup_service, stream_alert_service
from services.core import lang_service
from services.utils import embed_service

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
        probabilidad="Probabilidad de activación (0.1 a 100). Deja vacío para no cambiarla."
    )
    async def chaos(self, ctx: commands.Context, estado: bool, probabilidad: float = None):
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

    # ==========================================
    #           SUBGRUPO: STREAMALERT (YouTube)
    # ==========================================
    @setup.group(name="streamalert", description="Gestiona las alertas de nuevos vídeos de YouTube.")
    async def streamalert_group(self, ctx: commands.Context):
        """Subgrupo para gestionar alertas de subida de vídeos de YouTube."""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @streamalert_group.command(name="add", description="Añade un canal de YouTube para recibir alertas de vídeos.")
    @app_commands.describe(
        canal_usuario="ID del canal (UC...) o handle (ej: @ElRubiusOMG)",
        canal_discord="Canal de Discord donde enviar las alertas",
        rol="Rol a mencionar al enviar la alerta (opcional)"
    )
    async def streamalert_add(self, ctx: commands.Context, canal_usuario: str, canal_discord: discord.TextChannel, rol: discord.Role = None):
        """Registra un canal de YouTube en el sistema de alertas."""
        await ctx.defer(ephemeral=True)
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        
        success, resolved_id = await stream_alert_service.add_stream_alert(
            ctx.guild.id, "youtube", canal_usuario, canal_discord.id, rol.id if rol else 0
        )
        
        if not success:
            err_key = f"setup_streamalert_error_{resolved_id}"
            err_msg = lang_service.get_text(err_key, lang)
            # Fallback si por alguna razón no está la clave específica
            if err_msg == err_key:
                err_msg = resolved_id
            return await ctx.send(embed=embed_service.error(
                lang_service.get_text("title_error", lang), err_msg, lite=True
            ), ephemeral=True)
            
        # Alerta guardada con éxito
        msg = lang_service.get_text(
            "setup_streamalert_added", lang,
            channel=resolved_id, discord_channel=canal_discord.mention
        )
        await ctx.send(embed=embed_service.success(
            lang_service.get_text("title_success", lang), msg, lite=True
        ), ephemeral=True)

    @streamalert_group.command(name="remove", description="Elimina una alerta de YouTube configurada.")
    @app_commands.describe(canal_usuario="ID del canal o handle a eliminar")
    async def streamalert_remove(self, ctx: commands.Context, canal_usuario: str):
        """Elimina un canal de YouTube del sistema de alertas."""
        await ctx.defer(ephemeral=True)
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        
        removed = await stream_alert_service.remove_stream_alert(ctx.guild.id, "youtube", canal_usuario)
        
        if not removed:
            return await ctx.send(embed=embed_service.error(
                lang_service.get_text("title_error", lang),
                lang_service.get_text("setup_streamalert_not_found", lang),
                lite=True
            ), ephemeral=True)
            
        msg = lang_service.get_text("setup_streamalert_removed", lang, channel=canal_usuario)
        await ctx.send(embed=embed_service.success(
            lang_service.get_text("title_success", lang), msg, lite=True
        ), ephemeral=True)

    @streamalert_group.command(name="list", description="Muestra la lista de canales de YouTube monitoreados.")
    async def streamalert_list(self, ctx: commands.Context):
        """Muestra los canales de YouTube monitoreados en el servidor actual."""
        await ctx.defer(ephemeral=True)
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        
        alerts = await stream_alert_service.get_stream_alerts(ctx.guild.id)
        if not alerts:
            return await ctx.send(embed=embed_service.info(
                lang_service.get_text("setup_streamalert_list_title", lang),
                lang_service.get_text("setup_streamalert_empty", lang),
                lite=True
            ), ephemeral=True)
            
        lines = []
        for i, alert in enumerate(alerts, 1):
            ch_mention = f"<#{alert['discord_channel_id']}>"
            role_mention = f"<@&{alert['role_id']}>" if alert['role_id'] else lang_service.get_text("setup_disabled", lang)
            lines.append(f"{i}. **YouTube:** `{alert['channel_name']}` ➡️ {ch_mention} (Mención: {role_mention})")
            
        desc = "\n".join(lines)
        await ctx.send(embed=embed_service.info(
            lang_service.get_text("setup_streamalert_list_title", lang),
            desc
        ), ephemeral=True)

    # ==========================================
    #           SECCIÓN: DÍAS FESTIVOS
    # ==========================================
    @setup.command(name="festivedays", description="Configura el sistema de recordatorios de días festivos.")
    @app_commands.describe(
        estado="Activar (on) o desactivar (off) los recordatorios",
        canal="Canal donde se anunciarán las festividades",
        rol="Rol a mencionar cuando se anuncie una festividad (opcional)"
    )
    async def festivedays(self, ctx: commands.Context, estado: Literal["on", "off"], canal: discord.TextChannel = None, rol: discord.Role = None):
        """Configura el sistema de felicitación y recordatorios de días festivos (Navidad, Halloween, etc.)."""
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        
        if estado == "on":
            if not canal:
                return await ctx.send(embed=embed_service.error(
                    lang_service.get_text("title_error", lang),
                    lang_service.get_text("setup_festivedays_need_channel", lang),
                    lite=True
                ), ephemeral=True)
            
            updates = {
                "festivedays_enabled": 1,
                "festivedays_channel_id": canal.id,
                "festivedays_role_id": rol.id if rol else 0
            }
            display = f"ON | {canal.mention}" + (f" | {rol.mention}" if rol else "")
        else:
            updates = {
                "festivedays_enabled": 0,
                "festivedays_channel_id": 0,
                "festivedays_role_id": 0
            }
            display = lang_service.get_text("setup_disabled", lang)
            
        await self._apply_setup(ctx, updates, lang_service.get_text("setup_festivedays_label", lang), display)

async def setup(bot):
    await bot.add_cog(Configuracion(bot))