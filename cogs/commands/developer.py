import logging
import asyncio
import os
import tracemalloc
import platform
import sys
import time
import discord
from discord import app_commands
from discord.ext import commands
from typing import Literal
from services import db_service, embed_service, lang_service, pagination_service
from config import settings

logger = logging.getLogger(__name__)

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

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

    async def _get_psutil_info(self):
        return await asyncio.to_thread(self._get_psutil_info_sync)

    def _get_psutil_info_sync(self):
        if not HAS_PSUTIL: return {"available": False}
        try:
            proc = psutil.Process()
            with proc.oneshot():
                cpu_proc = proc.cpu_percent()
                mem_proc = proc.memory_info().rss / 1024 / 1024
                create_time = proc.create_time()
            
            return {
                "cpu_proc": cpu_proc, "mem_proc": mem_proc, "uptime": create_time,
                "cpu_sys": psutil.cpu_percent(), "ram_sys": psutil.virtual_memory(), 
                "disk": psutil.disk_usage(".") if os.path.exists(".") else None, "available": True
            }
        except Exception:
            return {"available": False}

    def _make_bar(self, percent, length=settings.UI_CONFIG["BAR_LENGTH"]):
        filled = int(length * percent / 100)
        return "█" * filled + "░" * (length - filled)

    async def get_general_embed(self):
        info = await self._get_psutil_info()
        lang = await lang_service.get_guild_lang(self.ctx.guild.id if self.ctx.guild else None)
        uptime_str = lang_service.get_text("serverinfo_na", lang)
        if info["available"]:
            uptime_seconds = int(time.time() - info["uptime"])
            m, s = divmod(uptime_seconds, 60)
            h, m = divmod(m, 60)
            d, h = divmod(h, 24)
            uptime_str = f"{d}d {h}h {m}m {s}s"

        embed = discord.Embed(title=f"{settings.BOTINFO_CONFIG['TITLE_EMOJI']} {lang_service.get_text('help_title', lang)}", color=settings.COLORS["INFO"])
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        embed.add_field(name=lang_service.get_text("botinfo_name", lang), value=f"{self.bot.user}", inline=True)
        embed.add_field(name=lang_service.get_text("botinfo_uptime", lang), value=f"`{uptime_str}`", inline=True)
        embed.add_field(name=lang_service.get_text("botinfo_python", lang), value=f"`{sys.version.split()[0]}`", inline=True)
        embed.add_field(name=lang_service.get_text("botinfo_lib", lang), value=f"`{discord.__version__}`", inline=True)
        embed.add_field(name=lang_service.get_text("botinfo_guilds", lang), value=f"{len(self.bot.guilds)}", inline=True)
        embed.add_field(name=lang_service.get_text("botinfo_users", lang), value=f"{len(self.bot.users)}", inline=True)
        return embed

    async def get_system_embed(self):
        info = await self._get_psutil_info()
        lang = await lang_service.get_guild_lang(self.ctx.guild.id if self.ctx.guild else None)
        embed = discord.Embed(title=lang_service.get_text("botinfo_system_title", lang), color=settings.COLORS["BLUE"])
        if not info["available"]:
            embed.description = lang_service.get_text("dev_psutil_error", await lang_service.get_guild_lang(self.ctx.guild.id if self.ctx.guild else None))
            return embed

        lang = await lang_service.get_guild_lang(self.ctx.guild.id if self.ctx.guild else None)
        embed.add_field(name=lang_service.get_text("botinfo_cpu", lang), value=f"`{info['cpu_proc']:.1f}%` / `{info['cpu_sys']:.1f}%`", inline=True)
        ram_bar = self._make_bar(info['ram_sys'].percent)
        embed.add_field(name=f"{lang_service.get_text('botinfo_ram', lang)} ({info['ram_sys'].percent}%)", value=f"{ram_bar}\nTotal: `{info['ram_sys'].total / 1024**3:.1f} GB`\nBot: `{info['mem_proc']:.1f} MB`", inline=False)
        if info['disk']:
            disk_bar = self._make_bar(info['disk'].percent)
            embed.add_field(name=f"{lang_service.get_text('botinfo_disk', lang)} ({info['disk'].percent}%)", value=f"{disk_bar}\nLibre: `{info['disk'].free / 1024**3:.1f} GB`", inline=False)
        embed.add_field(name=lang_service.get_text("botinfo_os", lang), value=f"{platform.system()} {platform.release()}", inline=True)
        return embed

    async def get_memory_embed(self):
        lang = await lang_service.get_guild_lang(self.ctx.guild.id if self.ctx.guild else None)
        embed = discord.Embed(title=lang_service.get_text("botinfo_memory_title", lang), color=settings.COLORS["GOLD"])
        if not tracemalloc.is_tracing():
            embed.description = lang_service.get_text("dev_mem_nodetail", lang)
            info = await self._get_psutil_info()
            if info["available"]: embed.add_field(name="Uso RSS", value=f"`{info['mem_proc']:.2f} MB`")
        else:
            snapshot = tracemalloc.take_snapshot()
            stats = snapshot.statistics('filename')
            
            # Inicializamos con las claves localizadas correctas para evitar KeyError
            key_cogs = lang_service.get_text("dev_mem_cogs", lang)
            key_services = lang_service.get_text("dev_mem_services", lang)
            key_libs = lang_service.get_text("dev_mem_libs", lang)
            key_others = lang_service.get_text("dev_mem_others", lang)
            grouped = {key_cogs: 0, key_services: 0, key_libs: 0, key_others: 0}
            
            details = []
            for stat in stats:
                path = stat.traceback[0].filename
                size = stat.size
                if "cogs" in path:
                    grouped[key_cogs] += size
                    details.append((f"🧩 {path.split('cogs')[-1].replace(os.sep, '/').lstrip('/')}", size))
                elif "services" in path:
                    grouped[key_services] += size
                    details.append((f"🛠️ {path.split('services')[-1].replace(os.sep, '/').lstrip('/')}", size))
                elif "site-packages" in path or "lib" in path: grouped[key_libs] += size
                else: grouped[key_others] += size
            
            desc = lang_service.get_text("dev_mem_summary", lang) + "\n".join([f"**{k}:** `{v/1024/1024:.2f} MB`" for k, v in grouped.items()])
            desc += "\n\n" + lang_service.get_text("dev_mem_top", lang)
            for name, size in sorted([d for d in details if "🧩" in d[0] or "🛠️" in d[0]], key=lambda x: x[1], reverse=True)[:10]:
                desc += f"`{name}`: **{size/1024:.1f} KB**\n"
            embed.description = desc
        return embed

    async def get_config_embed(self):
        lang = await lang_service.get_guild_lang(self.ctx.guild.id if self.ctx.guild else None)
        embed = discord.Embed(title=lang_service.get_text("botinfo_config_title", lang), color=settings.COLORS["TEAL"])
        embed.add_field(name=lang_service.get_text("botinfo_langs", lang), value=lang_service.get_text("lang_list", lang), inline=False)
        log_size = f"{os.path.getsize(settings.LOG_FILE)/1024:.1f} KB" if os.path.exists(settings.LOG_FILE) else "0 KB"
        embed.add_field(name=lang_service.get_text("botinfo_logfile", lang), value=f"`{log_size}`", inline=True)
        rows = await db_service.fetch_all("SELECT type, text FROM bot_statuses")
        status_txt = "\n".join([f"• [{r['type']}] {r['text']}" for r in rows[:5]]) + (f"\n... y {len(rows)-5} más." if len(rows) > 5 else "") if rows else lang_service.get_text("log_none", lang)
        embed.add_field(name=lang_service.get_text("botinfo_statuses", lang), value=status_txt, inline=False)
        return embed

    async def _update(self, interaction, embed, style_idx):
        for i, child in enumerate(self.children): child.style = discord.ButtonStyle.primary if i == style_idx else discord.ButtonStyle.secondary
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(style=discord.ButtonStyle.primary)
    async def btn_general(self, interaction: discord.Interaction, button: discord.ui.Button): await self._update(interaction, await self.get_general_embed(), 0)

    @discord.ui.button(style=discord.ButtonStyle.secondary)
    async def btn_system(self, interaction: discord.Interaction, button: discord.ui.Button): await self._update(interaction, await self.get_system_embed(), 1)

    @discord.ui.button(style=discord.ButtonStyle.secondary)
    async def btn_memory(self, interaction: discord.Interaction, button: discord.ui.Button): await self._update(interaction, await self.get_memory_embed(), 2)

    @discord.ui.button(style=discord.ButtonStyle.secondary)
    async def btn_config(self, interaction: discord.Interaction, button: discord.ui.Button): await self._update(interaction, await self.get_config_embed(), 3)

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
        # Optimización: Traer solo los últimos 25 registros en lugar de toda la tabla
        rows = await db_service.fetch_all(f"SELECT id, type, text FROM bot_statuses ORDER BY id DESC LIMIT {settings.DEV_CONFIG['STATUS_LIMIT']}")
        
        if not rows:
            return await ctx.send(embed=embed_service.warning(lang_service.get_text("title_status", lang), lang_service.get_text("status_empty", lang)), ephemeral=True)

        options = []
        for row in rows:
            label = f"[{row['type'].title()}] {row['text']}"
            limit = settings.UI_CONFIG["STATUS_TRUNCATE"]
            if len(label) > 100: label = label[:limit] + "..."
            options.append(discord.SelectOption(label=label, value=str(row['id']), emoji=lang_service.get_text("dev_status_item_emoji", lang)))

        ph = lang_service.get_text("status_placeholder", lang)
        view = StatusDeleteView(options, ph)
        
        await ctx.send(f"{settings.BOTINFO_CONFIG['SELECT_EMOJI']} **{ph}**", view=view, ephemeral=True)

    @commands.hybrid_command(name="listservers", description="Lista los servidores conectados (Solo Owner).", hidden=True)
    @commands.is_owner()
    async def listservers(self, ctx: commands.Context):
        await ctx.defer(ephemeral=True)
        
        guilds = sorted(self.bot.guilds, key=lambda g: g.member_count, reverse=True)
        # Como es comando de owner, podemos forzar español o usar el del server actual, usaremos el del server actual por consistencia
        lang = await lang_service.get_guild_lang(ctx.guild.id if ctx.guild else None)
        
        if not guilds:
            return await ctx.send(embed=embed_service.warning(lang_service.get_text("title_info", lang), lang_service.get_text("dev_servers_none", lang)), ephemeral=True)

        pages = []
        chunk_size = settings.DEV_CONFIG["SERVER_LIST_CHUNK_SIZE"]
        chunks = [guilds[i:i + chunk_size] for i in range(0, len(guilds), chunk_size)]

        for i, chunk in enumerate(chunks):
            desc = ""
            for guild in chunk:
                desc += lang_service.get_text("dev_servers_format", lang, 
                    name=guild.name, 
                    id=guild.id, 
                    members=guild.member_count, 
                    owner=guild.owner_id
                )
            
            embed = discord.Embed(title=lang_service.get_text("dev_servers_title", lang, count=len(self.bot.guilds)), description=desc, color=settings.COLORS["GOLD"])
            embed.set_footer(text=lang_service.get_text("dev_servers_page", lang, current=i+1, total=len(chunks)))
            pages.append(embed)

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
        desc = ""
        
        if HAS_PSUTIL:
            process = psutil.Process(os.getpid())
            mem = process.memory_info().rss / 1024 / 1024
            desc += lang_service.get_text("dev_mem_total", lang, mem=mem)
        
        if not tracemalloc.is_tracing():
            desc += lang_service.get_text("dev_mem_nodetail", lang)
        else:
            snapshot = tracemalloc.take_snapshot()
            stats = snapshot.statistics('filename')
            grouped = {}
            
            for stat in stats:
                path = stat.traceback[0].filename
                name = "🧩 " + path.split("cogs")[-1].replace("\\", "/").lstrip("/") if "cogs" in path else ("🛠️ " + path.split("services")[-1].replace("\\", "/").lstrip("/") if "services" in path else ("📚 Librerías" if "site-packages" in path else "📄 Otros"))
                grouped[name] = grouped.get(name, 0) + stat.size
            
            desc += "**📊 Top Consumo (Diferencial):**\n"
            for name, size in sorted(grouped.items(), key=lambda x: x[1], reverse=True)[:15]:
                desc += f"**{name}**: `{size/1024:.2f} KB`\n"

        await ctx.send(embed=embed_service.info(lang_service.get_text("botinfo_memory_title", lang), desc))

    @commands.hybrid_command(name="botinfo", description="Panel de control e información del sistema.")
    async def botinfo(self, ctx: commands.Context):
        lang = await lang_service.get_guild_lang(ctx.guild.id if ctx.guild else None)
        view = BotInfoView(ctx, self.bot, lang)
        embed = await view.get_general_embed()
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