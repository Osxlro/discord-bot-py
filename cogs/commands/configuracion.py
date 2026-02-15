import discord
from discord import app_commands
from discord.ext import commands
from typing import Literal
from services import db_service, embed_service, lang_service
from config import settings

class Configuracion(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # --- HELPER INTERNO ---
    async def _update_channel_config(self, ctx, key: str, channel: discord.TextChannel, label: str):
        """Helper centralizado para actualizar IDs de canales en la base de datos."""
        await ctx.defer(ephemeral=True)
        await db_service.update_guild_config(ctx.guild.id, {key: channel.id})
        
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        msg = lang_service.get_text("setup_desc", lang, type=label, value=channel.mention)
        await ctx.send(embed=embed_service.success(lang_service.get_text("setup_success", lang), msg), ephemeral=True)

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
        guild_id = ctx.guild.id
        config = await db_service.get_guild_config(guild_id)
        lang = config.get("language", "es")

        def get_ch(cid):
            ch = ctx.guild.get_channel(cid)
            return ch.mention if ch else "❌"

        def get_role(rid):
            role = ctx.guild.get_role(rid)
            return role.mention if role else "@everyone"

        embed = discord.Embed(
            title=f" {lang_service.get_text('serverinfo_config', lang)}",
            color=settings.COLORS["INFO"]
        )
        embed.set_author(name=ctx.guild.name, icon_url=ctx.guild.icon.url if ctx.guild.icon else None)

        ch_desc = (
            f"👋 **Bienvenida:** {get_ch(config.get('welcome_channel_id'))}\n"
            f"🤫 **Confesiones:** {get_ch(config.get('confessions_channel_id'))}\n"
            f"📜 **Logs:** {get_ch(config.get('logs_channel_id'))}\n"
            f"🎂 **Cumpleaños:** {get_ch(config.get('birthday_channel_id'))}\n"
            f"📖 **WordDay:** {get_ch(config.get('wordday_channel_id'))}"
        )
        embed.add_field(name=lang_service.get_text("setup_info_channels", lang), value=ch_desc, inline=False)

        chaos_status = "✅" if config.get("chaos_enabled") else "❌"
        chaos_prob = f"{config.get('chaos_probability', 0.01) * 100:.1f}%"
        
        settings_desc = (
            f"🌐 **Idioma:** {lang_service.get_text('lang_name_' + lang, lang)}\n"
            f"👋 **Despedida:** {'✅' if config.get('server_goodbye_msg') else '❌'}\n"
            f"🔫 **Chaos:** {chaos_status} ({chaos_prob})\n"
            f"📢 **Mención WordDay:** {get_role(config.get('wordday_role_id'))}"
        )
        embed.add_field(name=lang_service.get_text("setup_info_settings", lang), value=settings_desc, inline=False)

        await ctx.send(embed=embed, ephemeral=True)

    # --- SECCIÓN: CONFIGURACIÓN DE CANALES ---

    @setup.command(name="welcome", description="Establece el canal de bienvenidas.")
    @app_commands.describe(canal="Canal donde se enviarán las bienvenidas")
    async def bienvenida(self, ctx: commands.Context, canal: discord.TextChannel):
        await self._update_channel_config(ctx, "welcome_channel_id", canal, "Bienvenida")

    @setup.command(name="confess", description="Establece el canal de confesiones anónimas.")
    @app_commands.describe(canal="Canal para las confesiones")
    async def confesiones(self, ctx: commands.Context, canal: discord.TextChannel):
        await self._update_channel_config(ctx, "confessions_channel_id", canal, "Confesiones")

    @setup.command(name="logs", description="Establece el canal de registros (logs).")
    @app_commands.describe(canal="Canal para logs de moderación")
    async def logs(self, ctx: commands.Context, canal: discord.TextChannel):
        await self._update_channel_config(ctx, "logs_channel_id", canal, "Logs")

    @setup.command(name="birthday", description="Establece el canal de avisos de cumpleaños.")
    @app_commands.describe(canal="Canal para felicitaciones")
    async def cumpleanos(self, ctx: commands.Context, canal: discord.TextChannel):
        await self._update_channel_config(ctx, "birthday_channel_id", canal, "Cumpleaños")

    # --- SECCIÓN: AJUSTES DE COMPORTAMIENTO Y MENSAJES ---

    @setup.command(name="goodbye", description="Personaliza el mensaje de despedida.")
    @app_commands.describe(mensaje="Usa {user} para el nombre y {server} para el servidor. Escribe 'reset' para borrar.")
    async def goodbye(self, ctx: commands.Context, mensaje: str):
        """Actualiza el mensaje de despedida o lo resetea a NULL."""
        await ctx.defer(ephemeral=True)
        val = None if mensaje.lower() == "reset" else mensaje
        await db_service.update_guild_config(ctx.guild.id, {"server_goodbye_msg": val})
        
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        msg = lang_service.get_text("setup_msg_updated", lang)
        await ctx.send(embed=embed_service.success(lang_service.get_text("setup_success", lang), msg), ephemeral=True)

    @setup.command(name="lang", description="Cambia el idioma del bot en este servidor.")
    @app_commands.describe(opcion="Selecciona el idioma (Español/English)")
    async def lang(self, ctx: commands.Context, opcion: Literal["es", "en"]):
        """Cambia el idioma de respuesta del bot para el servidor actual."""
        await ctx.defer(ephemeral=True)
        await db_service.update_guild_config(ctx.guild.id, {"language": opcion})
        
        # Usamos el idioma seleccionado para responder
        lang = opcion
        display = "Español 🇪🇸" if opcion == "es" else "English 🇺🇸"
        
        msg = lang_service.get_text("setup_desc", lang, type="Idioma", value=display)
        await ctx.send(embed=embed_service.success(lang_service.get_text("setup_success", lang), msg), ephemeral=True)

    @setup.command(name="chaos", description="Configura el sistema Chaos (ruleta rusa).")
    @app_commands.describe(
        estado="Activar o desactivar el sistema",
        probabilidad="Probabilidad de activación (ej: 1 para 1%)"
    )
    async def chaos(self, ctx: commands.Context, estado: bool, probabilidad: float):
        """Configura la probabilidad y estado del sistema Chaos."""
        await ctx.defer(ephemeral=True)
        
        # Normalizar probabilidad (0.1% a 100%) y convertir a decimal para la DB
        prob_clamped = max(0.1, min(100.0, probabilidad))
        prob_decimal = prob_clamped / 100.0
        
        updates = {
            "chaos_enabled": 1 if estado else 0,
            "chaos_probability": prob_decimal
        }
        
        await db_service.update_guild_config(ctx.guild.id, updates)
        
        # Sincronizar con la caché del evento Chaos si el Cog está cargado
        chaos_cog = self.bot.get_cog("Chaos")
        if chaos_cog:
            chaos_cog.update_local_config(ctx.guild.id, estado, prob_decimal)
            
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        status_txt = "✅ Activado" if estado else "❌ Desactivado"
        msg = lang_service.get_text("setup_chaos_desc", lang, status=status_txt, prob=prob_clamped)
        
        await ctx.send(embed=embed_service.success(lang_service.get_text("setup_success", lang), msg), ephemeral=True)

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
        await self._update_channel_config(ctx, "wordday_channel_id", canal, "Frase del Día")

    @wordday_group.command(name="role", description="Establece el rol a mencionar.")
    @app_commands.describe(rol="Rol a mencionar")
    async def wordday_role(self, ctx: commands.Context, rol: discord.Role):
        await ctx.defer(ephemeral=True)
        await db_service.update_guild_config(ctx.guild.id, {"wordday_role_id": rol.id})
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        msg = lang_service.get_text("setup_desc", lang, type="Rol Frase del Día", value=rol.mention)
        await ctx.send(embed=embed_service.success(lang_service.get_text("setup_success", lang), msg), ephemeral=True)

async def setup(bot):
    await bot.add_cog(Configuracion(bot))