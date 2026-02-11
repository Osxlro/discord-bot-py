import logging
import tracemalloc
import discord
from discord import app_commands
from discord.ext import commands
from typing import Literal
from services import db_service, embed_service, lang_service, pagination_service, developer_service
from config import settings

logger = logging.getLogger(__name__)

class StatusSelect(discord.ui.Select):
    def __init__(self, options, placeholder_text):
        super().__init__(
            placeholder=placeholder_text,
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        status_id = int(self.values[0])
        await db_service.execute("DELETE FROM bot_statuses WHERE id = ?", (status_id,))
        logger.info(f"Status eliminado (ID: {status_id}) por {interaction.user}")
        
        lang = await lang_service.get_guild_lang(interaction.guild_id if interaction.guild_id else None)
        await interaction.response.edit_message(
            embed=embed_service.success(lang_service.get_text("title_status", lang), lang_service.get_text("dev_status_deleted", lang)), 
            view=None
        )

class StatusDeleteView(discord.ui.View):
    def __init__(self, options, placeholder_text):
        super().__init__(timeout=settings.TIMEOUT_CONFIG["STATUS_DELETE"])
        self.add_item(StatusSelect(options, placeholder_text))

class BotInfoView(discord.ui.View):
    def __init__(self, ctx, bot, lang):
        super().__init__(timeout=settings.TIMEOUT_CONFIG["BOT_INFO"])
        self.ctx = ctx
        self.bot = bot
        self.lang = lang

        # Localización de etiquetas y emojis de botones
        self.btn_general.label = lang_service.get_text("botinfo_btn_general", lang)
        self.btn_system.label = lang_service.get_text("botinfo_btn_system", lang)
        self.btn_memory.label = lang_service.get_text("botinfo_btn_memory", lang)
        self.btn_config.label = lang_service.get_text("botinfo_btn_config", lang)
        
        self.btn_general.emoji = settings.BOTINFO_CONFIG["EMOJIS"]["GENERAL"]
        self.btn_system.emoji = settings.BOTINFO_CONFIG["EMOJIS"]["SYSTEM"]
        self.btn_memory.emoji = settings.BOTINFO_CONFIG["EMOJIS"]["MEMORY"]
        self.btn_config.emoji = settings.BOTINFO_CONFIG["EMOJIS"]["CONFIG"]

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user.id != self.ctx.author.id:
            lang = await lang_service.get_guild_lang(interaction.guild_id if interaction.guild_id else None)
            await interaction.response.send_message(lang_service.get_text("dev_interaction_error", lang), ephemeral=True)
            return False
        return True

    async def _update(self, interaction, embed, style_idx):
        for i, child in enumerate(self.children): child.style = discord.ButtonStyle.primary if i == style_idx else discord.ButtonStyle.secondary
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(style=discord.ButtonStyle.primary)
    async def btn_general(self, interaction: discord.Interaction, button: discord.ui.Button): await self._update(interaction, await developer_service.get_general_embed(self.bot, self.ctx.guild, self.lang), 0)

    @discord.ui.button(style=discord.ButtonStyle.secondary)
    async def btn_system(self, interaction: discord.Interaction, button: discord.ui.Button): await self._update(interaction, await developer_service.get_system_embed(self.ctx.guild, self.lang), 1)

    @discord.ui.button(style=discord.ButtonStyle.secondary)
    async def btn_memory(self, interaction: discord.Interaction, button: discord.ui.Button): await self._update(interaction, await developer_service.get_memory_embed(self.lang), 2)

    @discord.ui.button(style=discord.ButtonStyle.secondary)
    async def btn_config(self, interaction: discord.Interaction, button: discord.ui.Button): await self._update(interaction, await developer_service.get_config_embed(self.lang), 3)

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
        rows = await db_service.fetch_all("SELECT type, text FROM bot_statuses")
        
        if not rows:
            return await ctx.send(embed=embed_service.warning(lang_service.get_text("title_status", lang), lang_service.get_text("status_empty", lang)), ephemeral=True)
        
        desc = lang_service.get_text("status_list_desc", lang) + "\n\n"
        for i, row in enumerate(rows, 1):
            desc += f"`{i}.` **[{row['type'].title()}]** {row['text']}\n"
            
        title = lang_service.get_text("status_list_title", lang)
        await ctx.send(embed=embed_service.info(title, desc), ephemeral=True)

    @status_group.command(name="agregar", description="Añade un nuevo estado a la rotación.")
    @app_commands.describe(tipo="Actividad", texto="Lo que se mostrará")
    async def agregar(self, ctx: commands.Context, tipo: Literal["playing", "watching", "listening", "competing"], texto: str):
        await db_service.execute("INSERT INTO bot_statuses (type, text) VALUES (?, ?)", (tipo, texto))
        logger.info(f"Status agregado: [{tipo}] {texto} por {ctx.author}")
        lang = await lang_service.get_guild_lang(ctx.guild.id if ctx.guild else None)
        msg = lang_service.get_text("status_add", lang, text=texto, type=tipo)

        await ctx.send(embed=embed_service.success(lang_service.get_text("dev_status_saved", lang), msg), ephemeral=True)

    @status_group.command(name="eliminar", description="Elimina un estado seleccionándolo de la lista.")
    async def eliminar(self, ctx: commands.Context):
        lang = await lang_service.get_guild_lang(ctx.guild.id if ctx.guild else None)
        options = await developer_service.get_status_delete_options(lang)

        if not options:
            return await ctx.send(embed=embed_service.warning(lang_service.get_text("title_status", lang), lang_service.get_text("status_empty", lang)), ephemeral=True)
        ph = lang_service.get_text("status_placeholder", lang)
        view = StatusDeleteView(options, ph)
        
        await ctx.send(f"{settings.BOTINFO_CONFIG['SELECT_EMOJI']} **{ph}**", view=view, ephemeral=True)

    @commands.hybrid_command(name="listservers", description="Lista los servidores conectados (Solo Owner).", hidden=True)
    @commands.is_owner()
    async def listservers(self, ctx: commands.Context):
        await ctx.defer(ephemeral=True)
        lang = await lang_service.get_guild_lang(ctx.guild.id if ctx.guild else None)
        pages = developer_service.get_server_list_chunks(self.bot, lang)

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
            synced = await self.bot.tree.sync()
            await msg.edit(content=lang_service.get_text("dev_sync_success", lang, count=len(synced)))
        except Exception as e:
            await msg.edit(content=lang_service.get_text("dev_sync_error", lang, error=e))

    @commands.hybrid_command(name="memoria", description="Analiza el consumo de RAM del bot.")
    @commands.is_owner()
    async def memoria(self, ctx: commands.Context, accion: Literal["ver", "iniciar", "detener"] = "ver"):
        lang = await lang_service.get_guild_lang(ctx.guild.id if ctx.guild else None)

        if accion == "iniciar":
            if not tracemalloc.is_tracing():
                tracemalloc.start()
                await ctx.send(embed=embed_service.success(lang_service.get_text("dev_mem_title", lang), lang_service.get_text("dev_mem_start", lang)))
            else:
                await ctx.send(embed=embed_service.warning(lang_service.get_text("dev_mem_title", lang), lang_service.get_text("dev_mem_active", lang)))
            return

        if accion == "detener":
            if tracemalloc.is_tracing():
                tracemalloc.stop()
                await ctx.send(embed=embed_service.success(lang_service.get_text("dev_mem_title", lang), lang_service.get_text("dev_mem_stop", lang)))
            else:
                await ctx.send(embed=embed_service.warning(lang_service.get_text("dev_mem_title", lang), lang_service.get_text("dev_mem_inactive", lang)))
            return

        # Accion: VER
        await ctx.defer()
        desc = await developer_service.get_memory_analysis(lang)
        await ctx.send(embed=embed_service.info(lang_service.get_text("botinfo_memory_title", lang), desc))

    @commands.hybrid_command(name="botinfo", description="Panel de control e información del sistema.")
    async def botinfo(self, ctx: commands.Context):
        lang = await lang_service.get_guild_lang(ctx.guild.id if ctx.guild else None)
        view = BotInfoView(ctx, self.bot, lang)
        embed = await developer_service.get_general_embed(self.bot, ctx.guild, lang)
        await ctx.send(embed=embed, view=view)

    @commands.hybrid_command(name="db_maintenance", description="Ejecuta mantenimiento (VACUUM) en la base de datos.")
    @commands.is_owner()
    async def db_maintenance(self, ctx: commands.Context):
        await ctx.defer()
        lang = await lang_service.get_guild_lang(ctx.guild.id if ctx.guild else None)
        # Ejecutamos VACUUM manualmente para compactar la DB
        await db_service.execute("VACUUM;")
        await ctx.send(embed=embed_service.success(lang_service.get_text("dev_db_maint_title", lang), lang_service.get_text("dev_db_maint_success", lang)))

async def setup(bot):
    await bot.add_cog(Developer(bot))