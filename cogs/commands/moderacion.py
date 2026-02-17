import discord
from discord.ext import commands
from discord import app_commands
from config import settings
from services.features import moderation_service
from services.core import db_service, lang_service
from services.utils import embed_service, pagination_service

class Moderacion(commands.Cog):
    """
    Cog encargado de las funciones de moderación del servidor.
    Proporciona herramientas para limpieza de mensajes, sanciones temporales (timeout),
    expulsiones, baneos y un sistema de advertencias (warns).
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_command(name="clear", description="Borra mensajes del chat.")
    @app_commands.describe(cantidad="Número de mensajes")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def clear(self, ctx: commands.Context, cantidad: int):
        """Elimina una cantidad específica de mensajes del canal actual."""
        # Obtener idioma y límites de configuración
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        max_msg = settings.CONFIG.get("moderation_config", {}).get("max_clear_msg", 100)

        # Validación de límite máximo para evitar abusos o errores de API
        if cantidad > max_msg:
            await ctx.reply(embed=embed_service.error(lang_service.get_text("title_error", lang), lang_service.get_text("clear_limit", lang, max=max_msg), lite=True), ephemeral=True)
            return

        # Diferir respuesta ya que purgar mensajes puede tardar
        await ctx.defer(ephemeral=True)
        # Delegar la purga al servicio
        embed, error = await moderation_service.handle_clear(ctx.channel, cantidad, lang)
        if error:
            return await ctx.send(embed=embed_service.warning(lang_service.get_text("title_info", lang), error, lite=True), ephemeral=True)
        
        # Enviar confirmación que se auto-elimina según la configuración
        delete_after = settings.CONFIG.get("moderation_config", {}).get("delete_after", 5)
        await ctx.send(embed=embed, delete_after=delete_after)

    @commands.hybrid_command(name="timeout", description="Aísla (Timeout) a un usuario.")
    @app_commands.describe(usuario="Miembro", tiempo="Ej: 10m, 1h", razon="Motivo")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def timeout(self, ctx: commands.Context, usuario: discord.Member, tiempo: str, razon: str = None):
        """Aísla temporalmente a un miembro, impidiéndole hablar o reaccionar."""
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        razon = razon or lang_service.get_text("mod_reason_default", lang)
        
        # El servicio maneja validaciones de jerarquía y formato de tiempo
        embed, error = await moderation_service.handle_timeout(ctx.author, usuario, tiempo, razon, lang)
        if error:
            return await ctx.reply(embed=embed_service.error(lang_service.get_text("title_error", lang), error, lite=True), ephemeral=True)
        await ctx.reply(embed=embed)
    
    @commands.hybrid_command(name="untimeout", description="Retira el aislamiento.")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def untimeout(self, ctx: commands.Context, usuario: discord.Member):
        """Elimina el aislamiento activo de un miembro."""
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        
        # Delegar la acción al servicio
        embed, error = await moderation_service.handle_untimeout(usuario, lang)
        if error:
            return await ctx.reply(embed=embed_service.error(lang_service.get_text("title_error", lang), error, lite=True), ephemeral=True)
        await ctx.reply(embed=embed)

    @commands.hybrid_command(name="kick", description="Expulsa a un miembro.")
    @app_commands.describe(usuario="Miembro", razon="Motivo")
    @app_commands.checks.has_permissions(kick_members=True)
    async def kick(self, ctx: commands.Context, usuario: discord.Member, razon: str = None):
        """Expulsa a un miembro del servidor."""
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        razon = razon or lang_service.get_text("mod_reason_default", lang)
        
        # El servicio orquesta la expulsión y la generación del embed (soporta mensajes personalizados)
        embed, error = await moderation_service.handle_kick(ctx.author, usuario, razon, lang)
        if error:
            # Determinar si el error es informativo (auto-acción) o crítico (jerarquía)
            title = lang_service.get_text("title_info", lang) if "self" in error else lang_service.get_text("title_error", lang)
            return await ctx.reply(embed=embed_service.error(title, error, lite=True), ephemeral=True)
        await ctx.reply(embed=embed)
            
    @commands.hybrid_command(name="ban", description="Banea a un miembro.")
    @app_commands.checks.has_permissions(ban_members=True)
    async def ban(self, ctx: commands.Context, usuario: discord.Member, razon: str = None):
        """Banea permanentemente a un miembro del servidor."""
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        razon = razon or lang_service.get_text("mod_reason_default", lang)
        
        # El servicio orquesta el baneo
        embed, error = await moderation_service.handle_ban(ctx.author, usuario, razon, lang)
        if error:
            title = lang_service.get_text("title_info", lang) if "self" in error else lang_service.get_text("title_error", lang)
            return await ctx.reply(embed=embed_service.error(title, error, lite=True), ephemeral=True)
        await ctx.reply(embed=embed)

    @commands.hybrid_command(name="warn", description="Advierte a un miembro.")
    @app_commands.describe(usuario="Miembro", razon="Motivo")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def warn(self, ctx: commands.Context, usuario: discord.Member, razon: str = None):
        """Registra una advertencia para un miembro en la base de datos."""
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        razon = razon or lang_service.get_text("mod_reason_default", lang)
        
        # El servicio maneja el guardado en DB y validaciones de jerarquía
        embed, error = await moderation_service.handle_warn(ctx.author, usuario, razon, lang)
        if error:
            title = lang_service.get_text("title_info", lang) if "self" in error else lang_service.get_text("title_error", lang)
            return await ctx.reply(embed=embed_service.error(title, error, lite=True), ephemeral=True)
        await ctx.reply(embed=embed)

    @commands.hybrid_command(name="warns", description="Muestra las advertencias de un usuario.")
    @app_commands.describe(usuario="Miembro")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def list_warns(self, ctx: commands.Context, usuario: discord.Member):
        """Muestra el historial de advertencias de un miembro con paginación."""
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        
        # El servicio recupera los datos y genera las páginas de embeds
        pages, error = await moderation_service.handle_list_warns(ctx.guild, usuario, lang)
        
        if error:
            # Si no hay advertencias, el servicio devuelve un mensaje informativo
            return await ctx.reply(embed=embed_service.info(lang_service.get_text("title_info", lang), error, lite=True))

        if len(pages) == 1:
            await ctx.reply(embed=pages[0])
        else:
            # Usar el sistema de paginación si hay muchos registros
            view = pagination_service.Paginator(pages, ctx.author.id)
            view.message = await ctx.send(embed=pages[0], view=view)

    @commands.hybrid_command(name="clearwarns", description="Limpia las advertencias de un usuario.")
    @app_commands.describe(usuario="Miembro")
    @app_commands.checks.has_permissions(administrator=True)
    async def clear_warns(self, ctx: commands.Context, usuario: discord.Member):
        """Elimina todas las advertencias registradas de un miembro."""
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        
        # Acción directa vía servicio
        embed = await moderation_service.handle_clear_warns(ctx.guild.id, usuario, lang)
        await ctx.reply(embed=embed)

    @commands.hybrid_command(name="delwarn", description="Elimina una advertencia específica por su ID.")
    @app_commands.describe(id="ID de la advertencia")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def delwarn(self, ctx: commands.Context, id: int):
        """Elimina un registro de advertencia individual usando su identificador único."""
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        
        # El servicio busca y elimina el ID si pertenece al servidor actual
        embed, error = await moderation_service.handle_delwarn(ctx.guild.id, id, lang)
        if error:
            return await ctx.reply(embed=embed_service.error(lang_service.get_text("title_error", lang), error, lite=True), ephemeral=True)
        await ctx.reply(embed=embed)

async def setup(bot: commands.Bot):
    """Función de entrada para cargar el Cog en el bot."""
    await bot.add_cog(Moderacion(bot))