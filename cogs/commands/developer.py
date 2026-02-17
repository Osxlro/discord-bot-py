import logging
import discord
from discord import app_commands
from discord.ext import commands
from typing import Literal
from services.features import developer_service
from config import settings
from services.core import lang_service
from services.utils import embed_service, pagination_service

logger = logging.getLogger(__name__)

class Developer(commands.Cog):
    """
    Cog de administración y desarrollo.
    Contiene comandos para gestionar el estado del bot, monitorizar el sistema
    y realizar tareas de mantenimiento técnico.
    """
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_group(name="status", description="Gestiona los estados rotativos del bot.")
    @commands.check_any(commands.is_owner(), commands.has_permissions(administrator=True))
    async def status_group(self, ctx: commands.Context):
        """Grupo de comandos para la gestión de la presencia (status) del bot."""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @status_group.command(name="listar", description="Muestra la lista de estados configurados.")
    async def listar(self, ctx: commands.Context):
        """
        Muestra todos los estados almacenados en la base de datos.
        La respuesta es efímera para no saturar el canal público.
        """
        # Obtener el idioma configurado para el servidor o el por defecto
        lang = await lang_service.get_guild_lang(ctx.guild.id if ctx.guild else None)
        
        # Delegar la obtención del embed al servicio
        embed = await developer_service.handle_list_statuses(lang)
        await ctx.send(embed=embed, ephemeral=True)

    @status_group.command(name="agregar", description="Añade un nuevo estado a la rotación.")
    @app_commands.describe(tipo="Actividad", texto="Lo que se mostrará")
    async def agregar(self, ctx: commands.Context, tipo: Literal["playing", "watching", "listening", "competing"], texto: str):
        """
        Añade una nueva frase a la rotación de estados del bot.
        """
        lang = await lang_service.get_guild_lang(ctx.guild.id if ctx.guild else None)
        
        # El servicio maneja el guardado en DB y retorna el embed de éxito
        embed = await developer_service.handle_add_status(tipo, texto, str(ctx.author), lang)
        await ctx.send(embed=embed, ephemeral=True)

    @status_group.command(name="eliminar", description="Elimina un estado seleccionándolo de la lista.")
    async def eliminar(self, ctx: commands.Context):
        """
        Muestra un menú desplegable (Select) para eliminar estados existentes.
        """
        lang = await lang_service.get_guild_lang(ctx.guild.id if ctx.guild else None)
        
        # El servicio prepara la vista interactiva con las opciones de la DB
        view, ph = await developer_service.handle_delete_status_prompt(lang)

        if not view:
            # Si no hay estados que borrar, avisamos al usuario
            return await ctx.send(embed=embed_service.warning(lang_service.get_text("title_status", lang), lang_service.get_text("status_empty", lang)), ephemeral=True)
        
        await ctx.send(f"{settings.BOTINFO_CONFIG['SELECT_EMOJI']} **{ph}**", view=view, ephemeral=True)

    @commands.hybrid_command(name="listservers", description="Lista los servidores conectados (Solo Owner).", hidden=True)
    @commands.is_owner()
    async def listservers(self, ctx: commands.Context):
        """
        Lista todos los servidores donde el bot está presente.
        Solo accesible por el dueño del bot.
        """
        await ctx.defer(ephemeral=True)
        lang = await lang_service.get_guild_lang(ctx.guild.id if ctx.guild else None)
        
        # Obtener lista paginada de servidores desde el servicio
        pages = await developer_service.handle_list_servers(self.bot, lang)

        if not pages:
            return await ctx.send(embed=embed_service.warning(lang_service.get_text("title_info", lang), lang_service.get_text("dev_servers_none", lang)), ephemeral=True)

        if len(pages) == 1:
            await ctx.send(embed=pages[0], ephemeral=True)
        else:
            view = pagination_service.Paginator(pages, ctx.author.id)
            view.message = await ctx.send(embed=pages[0], view=view, ephemeral=True)

    @commands.command(name="sync", hidden=True)
    @commands.is_owner()
    async def sync(self, ctx: commands.Context):
        """
        Sincroniza los comandos de aplicación (Slash Commands) con Discord.
        Útil cuando se añaden o modifican comandos nuevos.
        """
        lang = await lang_service.get_guild_lang(ctx.guild.id if ctx.guild else None)
        msg_obj = await ctx.send(lang_service.get_text("dev_sync_start", lang))
        
        # Ejecutar sincronización global
        content, error = await developer_service.handle_sync(self.bot, lang)
        await msg_obj.edit(content=content or error)

    @commands.hybrid_command(name="botinfo", description="Panel de control e información del sistema.")
    async def botinfo(self, ctx: commands.Context):
        """
        Muestra un panel interactivo con estadísticas de uso de CPU, RAM,
        versiones de librerías y tiempos de actividad (Uptime).
        """
        lang = await lang_service.get_guild_lang(ctx.guild.id if ctx.guild else None)
        
        # El servicio orquesta la recolección de datos de psutil y la creación de la vista
        embed, view = await developer_service.handle_bot_info(ctx, self.bot, lang)
        view.message = await ctx.send(embed=embed, view=view)

    @commands.hybrid_command(name="db_maintenance", description="Ejecuta mantenimiento (VACUUM) en la base de datos.")
    @commands.is_owner()
    async def db_maintenance(self, ctx: commands.Context):
        """
        Ejecuta el comando VACUUM en SQLite para optimizar el tamaño del archivo
        y defragmentar la base de datos.
        """
        await ctx.defer()
        lang = await lang_service.get_guild_lang(ctx.guild.id if ctx.guild else None)
        embed = await developer_service.handle_db_maintenance(lang)
        await ctx.send(embed=embed)

    @commands.command(name="restart", hidden=True)
    @commands.is_owner()
    async def restart(self, ctx: commands.Context):
        """
        Reinicia el proceso del bot de forma segura, cerrando la base de datos primero.
        """
        lang = await lang_service.get_guild_lang(ctx.guild.id if ctx.guild else None)
        await ctx.send(lang_service.get_text("dev_restart_msg", lang))
        # El servicio se encarga de la ejecución del sistema para el reinicio
        await developer_service.restart_bot(str(ctx.author))

async def setup(bot):
    await bot.add_cog(Developer(bot))