import logging
import discord
from discord import app_commands
from discord.ext import commands
from typing import Literal
from services.features import developer_service
from ui import developer_ui
from config import settings
from services.core import lang_service
from services.utils import embed_service, pagination_service

logger = logging.getLogger(__name__)

class Developer(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_group(name="status", description="Gestiona los estados rotativos del bot.")
    @commands.check_any(commands.is_owner(), commands.has_permissions(administrator=True))
    async def status_group(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @status_group.command(name="listar", description="Muestra la lista de estados configurados.")
    async def listar(self, ctx: commands.Context):
        # Listado solo para el admin (EPHEMERAL)
        lang = await lang_service.get_guild_lang(ctx.guild.id if ctx.guild else None)
        embed = await developer_ui.get_status_list_embed(lang)
        await ctx.send(embed=embed, ephemeral=True)

    @status_group.command(name="agregar", description="Añade un nuevo estado a la rotación.")
    @app_commands.describe(tipo="Actividad", texto="Lo que se mostrará")
    async def agregar(self, ctx: commands.Context, tipo: Literal["playing", "watching", "listening", "competing"], texto: str):
        await developer_service.add_bot_status(tipo, texto, str(ctx.author))
        lang = await lang_service.get_guild_lang(ctx.guild.id if ctx.guild else None)
        msg = lang_service.get_text("status_add", lang, text=texto, type=tipo)

        await ctx.send(embed=embed_service.success(lang_service.get_text("dev_status_saved", lang), msg), ephemeral=True)

    @status_group.command(name="eliminar", description="Elimina un estado seleccionándolo de la lista.")
    async def eliminar(self, ctx: commands.Context):
        lang = await lang_service.get_guild_lang(ctx.guild.id if ctx.guild else None)
        options = await developer_ui.get_status_delete_options(lang)

        if not options:
            return await ctx.send(embed=embed_service.warning(lang_service.get_text("title_status", lang), lang_service.get_text("status_empty", lang)), ephemeral=True)
        ph = lang_service.get_text("status_placeholder", lang)
        view = developer_ui.StatusDeleteView(options, ph)
        
        await ctx.send(f"{settings.BOTINFO_CONFIG['SELECT_EMOJI']} **{ph}**", view=view, ephemeral=True)

    @commands.hybrid_command(name="listservers", description="Lista los servidores conectados (Solo Owner).", hidden=True)
    @commands.is_owner()
    async def listservers(self, ctx: commands.Context):
        await ctx.defer(ephemeral=True)
        lang = await lang_service.get_guild_lang(ctx.guild.id if ctx.guild else None)
        pages = developer_ui.get_server_list_chunks(self.bot, lang)

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
        lang = await lang_service.get_guild_lang(ctx.guild.id if ctx.guild else None)
        msg = await ctx.send(lang_service.get_text("dev_sync_start", lang))
        try:
            synced = await developer_service.sync_commands(self.bot)
            await msg.edit(content=lang_service.get_text("dev_sync_success", lang, count=len(synced)))
        except Exception as e:
            await msg.edit(content=lang_service.get_text("dev_sync_error", lang, error=e))

    @commands.hybrid_command(name="botinfo", description="Panel de control e información del sistema.")
    async def botinfo(self, ctx: commands.Context):
        lang = await lang_service.get_guild_lang(ctx.guild.id if ctx.guild else None)
        view = developer_ui.BotInfoView(ctx, self.bot, lang)
        embed = await developer_ui.get_general_embed(self.bot, ctx.guild, lang)
        view.message = await ctx.send(embed=embed, view=view)

    @commands.hybrid_command(name="db_maintenance", description="Ejecuta mantenimiento (VACUUM) en la base de datos.")
    @commands.is_owner()
    async def db_maintenance(self, ctx: commands.Context):
        await ctx.defer()
        lang = await lang_service.get_guild_lang(ctx.guild.id if ctx.guild else None)
        await developer_service.perform_db_maintenance()
        await ctx.send(embed=embed_service.success(lang_service.get_text("dev_db_maint_title", lang), lang_service.get_text("dev_db_maint_success", lang)))

    @commands.command(name="restart", hidden=True)
    @commands.is_owner()
    async def restart(self, ctx: commands.Context):
        lang = await lang_service.get_guild_lang(ctx.guild.id if ctx.guild else None)
        await ctx.send(lang_service.get_text("dev_restart_msg", lang))
        await developer_service.restart_bot(str(ctx.author))

async def setup(bot):
    await bot.add_cog(Developer(bot))