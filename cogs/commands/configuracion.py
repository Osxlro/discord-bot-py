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

    # --- COMANDOS UNIFICADOS DE CONFIGURACIÓN ---

    @setup.command(name="channel", description="Configura los canales de los distintos sistemas del bot.")
    @app_commands.describe(
        tipo="El sistema a configurar",
        canal="Canal de Discord a asociar (deja vacío para desactivar)"
    )
    async def setup_channel(self, ctx: commands.Context, tipo: Literal["welcome", "confess", "logs", "birthday", "wordday", "festivedays"], canal: discord.TextChannel = None):
        """Asigna o desactiva el canal para un sistema en específico."""
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        
        # Mapeo de tipo al nombre de la columna en la base de datos
        col_map = {
            "welcome": "welcome_channel_id",
            "confess": "confessions_channel_id",
            "logs": "logs_channel_id",
            "birthday": "birthday_channel_id",
            "wordday": "wordday_channel_id",
            "festivedays": "festivedays_channel_id"
        }
        
        # Mapeo del label localized
        label_map = {
            "welcome": "setup_label_welcome",
            "confess": "setup_label_confess",
            "logs": "setup_label_logs",
            "birthday": "setup_label_birthday",
            "wordday": "setup_label_wordday_ch",
            "festivedays": "setup_label_festivedays"
        }
        
        col = col_map[tipo]
        label = lang_service.get_text(label_map[tipo], lang)
        
        val = canal.id if canal else 0
        display = canal.mention if canal else lang_service.get_text("setup_disabled", lang)
        
        # Actualización
        await self._apply_setup(ctx, {col: val}, label, display)

    @setup.command(name="role", description="Configura los roles de los distintos sistemas del bot.")
    @app_commands.describe(
        tipo="El sistema a configurar",
        rol="Rol de Discord a asociar (deja vacío para desactivar)"
    )
    async def setup_role(self, ctx: commands.Context, tipo: Literal["autorole", "wordday", "festivedays"], rol: discord.Role = None):
        """Asigna o desactiva el rol para un sistema en específico."""
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        
        col_map = {
            "autorole": "autorole_id",
            "wordday": "wordday_role_id",
            "festivedays": "festivedays_role_id"
        }
        
        label_map = {
            "autorole": "setup_label_autorole",
            "wordday": "setup_label_wordday_role",
            "festivedays": "setup_label_festivedays"
        }
        
        col = col_map[tipo]
        label = lang_service.get_text(label_map[tipo], lang)
        
        val = rol.id if rol else 0
        display = rol.mention if rol else lang_service.get_text("setup_disabled", lang)
        
        await self._apply_setup(ctx, {col: val}, label, display)

    @setup.command(name="message", description="Personaliza los mensajes de texto del bot.")
    @app_commands.describe(
        tipo="El tipo de mensaje a configurar",
        texto="Contenido del mensaje (deja vacío o escribe 'reset' para desactivar)"
    )
    async def setup_message(self, ctx: commands.Context, tipo: Literal["goodbye"], texto: str = None):
        """Personaliza textos y mensajes de salida del servidor."""
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        
        col_map = {
            "goodbye": "server_goodbye_msg"
        }
        
        label_map = {
            "goodbye": "goodbye_title"
        }
        
        col = col_map[tipo]
        label = lang_service.get_text(label_map[tipo], lang)
        
        val = None if not texto or texto.lower() == "reset" else texto
        display = val if val else lang_service.get_text("setup_disabled", lang)
        
        await self._apply_setup(ctx, {col: val}, label, display)

    @setup.command(name="system", description="Configura e inicializa sistemas generales del bot.")
    @app_commands.describe(
        tipo="El sistema a configurar",
        estado="Encender (on) o apagar (off) el sistema",
        probabilidad="Probabilidad de ruleta rusa (0.1 a 100). Solo para Chaos."
    )
    async def setup_system(self, ctx: commands.Context, tipo: Literal["chaos", "festivedays"], estado: Literal["on", "off"], probabilidad: float = None):
        """Permite habilitar o inhabilitar sistemas como Chaos o Días Festivos."""
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        is_on = (estado == "on")
        
        if tipo == "chaos":
            # Delegar a setup_service que ya gestiona la probabilidad de Chaos
            embed = await setup_service.handle_chaos_setup(self.bot, ctx.guild.id, is_on, probabilidad, lang)
            await ctx.send(embed=embed, ephemeral=True)
        else: # festivedays
            updates = {
                "festivedays_enabled": 1 if is_on else 0
            }
            if not is_on:
                updates["festivedays_channel_id"] = 0
                updates["festivedays_role_id"] = 0
                
            label = lang_service.get_text("setup_label_festivedays", lang)
            display = "ON" if is_on else lang_service.get_text("setup_disabled", lang)
            await self._apply_setup(ctx, updates, label, display)

    @setup.command(name="lang", description="Cambia el idioma del bot en este servidor.")
    @app_commands.describe(opcion="Selecciona el idioma (es/en/pt/fr)")
    async def lang(self, ctx: commands.Context, opcion: Literal["es", "en", "pt", "fr"]):
        """Cambia el idioma de interacción del bot en el servidor."""
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        display_map = {"es": "Español 🇪🇸", "en": "English 🇺🇸", "pt": "Português 🇵🇹", "fr": "Français 🇫🇷"}
        display = display_map.get(opcion, "Unknown")
        label = lang_service.get_text("setup_label_language", lang)
        await self._apply_setup(ctx, {"language": opcion}, label, display)

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

async def setup(bot):
    await bot.add_cog(Configuracion(bot))