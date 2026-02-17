import discord
import tracemalloc
import os
import sys
import platform
import time
import asyncio
from config import settings
from services.core import lang_service, db_service
from services.utils import embed_service

def _make_bar(percent, length=settings.UI_CONFIG["BAR_LENGTH"]):
    filled = int(length * percent / 100)
    return "█" * filled + "░" * (length - filled)

async def get_general_embed(bot, guild, lang, info=None):
    if info is None:
        from services.features import developer_service
        info = await developer_service.get_psutil_info()
        
    uptime_str = lang_service.get_text("serverinfo_na", lang)
    if info["available"]:
        uptime_seconds = int(time.time() - info["uptime"])
        m, s = divmod(uptime_seconds, 60)
        h, m = divmod(m, 60)
        d, h = divmod(h, 24)
        uptime_str = f"{d}d {h}h {m}m {s}s"

    embed = discord.Embed(title=f"{settings.BOTINFO_CONFIG['TITLE_EMOJI']} {lang_service.get_text('help_title', lang)}", color=settings.COLORS["INFO"])
    embed.set_thumbnail(url=bot.user.display_avatar.url)
    embed.add_field(name=lang_service.get_text("botinfo_name", lang), value=f"{bot.user}", inline=True)
    embed.add_field(name=lang_service.get_text("botinfo_uptime", lang), value=f"`{uptime_str}`", inline=True)
    embed.add_field(name=lang_service.get_text("botinfo_python", lang), value=f"`{sys.version.split()[0]}`", inline=True)
    embed.add_field(name=lang_service.get_text("botinfo_lib", lang), value=f"`{discord.__version__}`", inline=True)
    embed.add_field(name=lang_service.get_text("botinfo_guilds", lang), value=f"{len(bot.guilds)}", inline=True)
    embed.add_field(name=lang_service.get_text("botinfo_users", lang), value=f"{len(bot.users)}", inline=True)
    return embed

async def get_system_embed(guild, lang, info=None):
    if info is None:
        from services.features import developer_service
        info = await developer_service.get_psutil_info()
        
    embed = discord.Embed(title=lang_service.get_text("botinfo_system_title", lang), color=settings.COLORS["BLUE"])
    if not info["available"]:
        embed.description = lang_service.get_text("dev_psutil_error", lang)
        return embed

    embed.add_field(name=lang_service.get_text("botinfo_cpu", lang), value=f"`{info['cpu_proc']:.1f}%` / `{info['cpu_sys']:.1f}%`", inline=True)
    ram_bar = _make_bar(info['ram_sys'].percent)
    embed.add_field(name=f"{lang_service.get_text('botinfo_ram', lang)} ({info['ram_sys'].percent}%)", value=f"{ram_bar}\nTotal: `{info['ram_sys'].total / 1024**3:.1f} GB`\nBot: `{info['mem_proc']:.1f} MB`", inline=False)
    if info['disk']:
        disk_bar = _make_bar(info['disk'].percent)
        embed.add_field(name=f"{lang_service.get_text('botinfo_disk', lang)} ({info['disk'].percent}%)", value=f"{disk_bar}\nLibre: `{info['disk'].free / 1024**3:.1f} GB`", inline=False)
    embed.add_field(name=lang_service.get_text("botinfo_os", lang), value=f"{platform.system()} {platform.release()}", inline=True)
    return embed

async def get_memory_embed(lang, info=None):
    embed = discord.Embed(title=lang_service.get_text("botinfo_memory_title", lang), color=settings.COLORS["GOLD"])
    if not tracemalloc.is_tracing():
        embed.description = lang_service.get_text("dev_mem_nodetail", lang)
        if info is None:
            from services.features import developer_service
            info = await developer_service.get_psutil_info()
            
        if info["available"]: embed.add_field(name="Uso RSS", value=f"`{info['mem_proc']:.2f} MB`")
    else:
        snapshot = tracemalloc.take_snapshot()
        stats = snapshot.statistics('filename')
        
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

async def get_config_embed(lang: str) -> discord.Embed:
    p_stats = await db_service.get_persistence_stats()
    embed = discord.Embed(title=lang_service.get_text("botinfo_config_title", lang), color=0x5865F2)
    embed.add_field(name=lang_service.get_text("botinfo_langs", lang), value=lang_service.get_text("lang_list", lang), inline=False)
    log_size = f"{os.path.getsize(settings.LOG_FILE)/1024:.1f} KB" if os.path.exists(settings.LOG_FILE) else "0 KB"
    embed.add_field(name=lang_service.get_text("botinfo_logfile", lang), value=f"`{log_size}`", inline=True)

    embed.add_field(
        name=lang_service.get_text("botinfo_persistence", lang), 
        value=lang_service.get_text("botinfo_persistence_desc", lang, count=p_stats['count'], size=p_stats['size_kb']), 
        inline=False
    )

    rows = await db_service.fetch_all("SELECT type, text FROM bot_statuses")
    status_txt = "\n".join([f"• [{r['type']}] {r['text']}" for r in rows[:5]]) + (lang_service.get_text("dev_status_more", lang, count=len(rows)-5) if len(rows) > 5 else "") if rows else lang_service.get_text("log_none", lang)
    embed.add_field(name=lang_service.get_text("botinfo_statuses", lang), value=status_txt, inline=False)
    return embed

async def get_status_list_embed(lang: str) -> discord.Embed:
    """Genera un embed con la lista de estados configurados."""
    rows = await db_service.fetch_all("SELECT type, text FROM bot_statuses")
    
    if not rows:
        return embed_service.warning(lang_service.get_text("title_status", lang), lang_service.get_text("status_empty", lang))
    
    desc = lang_service.get_text("status_list_desc", lang) + "\n\n"
    for i, row in enumerate(rows, 1):
        desc += f"`{i}.` **[{row['type'].title()}]** {row['text']}\n"
        
    title = lang_service.get_text("status_list_title", lang)
    return embed_service.info(title, desc)

async def get_status_delete_options(lang):
    rows = await db_service.fetch_all(f"SELECT id, type, text FROM bot_statuses ORDER BY id DESC LIMIT {settings.DEV_CONFIG['STATUS_LIMIT']}")
    if not rows: return None

    options = []
    for row in rows:
        label = f"[{row['type'].title()}] {row['text']}"
        limit = settings.UI_CONFIG["STATUS_TRUNCATE"]
        if len(label) > 100: label = label[:limit] + "..."
        options.append(discord.SelectOption(label=label, value=str(row['id']), emoji=lang_service.get_text("dev_status_item_emoji", lang)))
    return options

def get_server_list_chunks(bot, lang):
    guilds = sorted(bot.guilds, key=lambda g: g.member_count, reverse=True)
    if not guilds: return []

    pages = []
    chunk_size = settings.DEV_CONFIG["SERVER_LIST_CHUNK_SIZE"]
    chunks = [guilds[i:i + chunk_size] for i in range(0, len(guilds), chunk_size)]

    for i, chunk in enumerate(chunks):
        desc = ""
        for guild in chunk:
            desc += lang_service.get_text("dev_servers_format", lang, 
                name=guild.name, id=guild.id, members=guild.member_count, owner=guild.owner_id
            )
        
        embed = discord.Embed(title=lang_service.get_text("dev_servers_title", lang, count=len(bot.guilds)), description=desc, color=settings.COLORS["GOLD"])
        embed.set_footer(text=lang_service.get_text("dev_servers_page", lang, current=i+1, total=len(chunks)))
        pages.append(embed)
    return pages

def get_status_add_success_embed(lang: str, texto: str, tipo: str) -> discord.Embed:
    """Genera el embed de éxito al añadir un estado."""
    msg = lang_service.get_text("status_add", lang, text=texto, type=tipo)
    return embed_service.success(lang_service.get_text("dev_status_saved", lang), msg)

def get_db_maint_success_embed(lang: str) -> discord.Embed:
    """Genera el embed de éxito al realizar mantenimiento de DB."""
    return embed_service.success(lang_service.get_text("dev_db_maint_title", lang), lang_service.get_text("dev_db_maint_success", lang))

class StatusSelect(discord.ui.Select):
    def __init__(self, options, placeholder_text):
        super().__init__(placeholder=placeholder_text, min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        status_id = int(self.values[0])
        from services.features import developer_service
        await developer_service.delete_bot_status(status_id, str(interaction.user))
        lang = await lang_service.get_guild_lang(interaction.guild_id if interaction.guild_id else None)
        await interaction.response.edit_message(embed=embed_service.success(lang_service.get_text("title_status", lang), lang_service.get_text("dev_status_deleted", lang)), view=None)

class StatusDeleteView(discord.ui.View):
    def __init__(self, options, placeholder_text):
        super().__init__(timeout=settings.TIMEOUT_CONFIG["STATUS_DELETE"])
        self.add_item(StatusSelect(options, placeholder_text))

class BotInfoView(discord.ui.View):
    def __init__(self, ctx, bot, lang):
        super().__init__(timeout=settings.TIMEOUT_CONFIG["BOT_INFO"])
        self.ctx, self.bot, self.lang = ctx, bot, lang
        self.active_tab, self.message = 0, None
        self.btn_general.label = lang_service.get_text("botinfo_btn_general", lang)
        self.btn_system.label = lang_service.get_text("botinfo_btn_system", lang)
        self.btn_memory.label = lang_service.get_text("botinfo_btn_memory", lang)
        self.btn_config.label = lang_service.get_text("botinfo_btn_config", lang)
        self.btn_general.emoji = settings.BOTINFO_CONFIG["EMOJIS"]["GENERAL"]
        self.btn_system.emoji = settings.BOTINFO_CONFIG["EMOJIS"]["SYSTEM"]
        self.btn_memory.emoji = settings.BOTINFO_CONFIG["EMOJIS"]["MEMORY"]
        self.btn_config.emoji = settings.BOTINFO_CONFIG["EMOJIS"]["CONFIG"]
        self.btn_monitor.label = "Iniciar Monitor"
        self.remove_item(self.btn_monitor)

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user.id != self.ctx.author.id:
            lang = await lang_service.get_guild_lang(interaction.guild_id if interaction.guild_id else None)
            await interaction.response.send_message(lang_service.get_text("dev_interaction_error", lang), ephemeral=True)
            return False
        return True

    async def on_timeout(self):
        if tracemalloc.is_tracing(): tracemalloc.stop()
        for child in self.children: child.disabled = True
        try: await self.message.edit(view=self)
        except: pass

    async def _monitor_loop(self):
        for _ in range(24):
            await asyncio.sleep(5)
            if self.active_tab != 2 or not tracemalloc.is_tracing(): break
            try:
                embed = await get_memory_embed(self.lang)
                embed.set_footer(text="🔴 Monitoreo en vivo activo (Auto-stop en 2 min)")
                await self.message.edit(embed=embed)
            except Exception: break
        if tracemalloc.is_tracing(): tracemalloc.stop()
        self.btn_monitor.label, self.btn_monitor.style = "Iniciar Monitor", discord.ButtonStyle.success
        try: await self.message.edit(view=self)
        except: pass

    async def _update(self, interaction, embed, style_idx):
        self.active_tab = style_idx
        if style_idx == 2:
            if self.btn_monitor not in self.children: self.add_item(self.btn_monitor)
        else:
            if self.btn_monitor in self.children: self.remove_item(self.btn_monitor)
        tabs = [self.btn_general, self.btn_system, self.btn_memory, self.btn_config]
        for i, child in enumerate(tabs): child.style = discord.ButtonStyle.primary if i == style_idx else discord.ButtonStyle.secondary
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(style=discord.ButtonStyle.primary)
    async def btn_general(self, interaction: discord.Interaction, button: discord.ui.Button): await self._update(interaction, await get_general_embed(self.bot, self.ctx.guild, self.lang), 0)
    @discord.ui.button(style=discord.ButtonStyle.secondary)
    async def btn_system(self, interaction: discord.Interaction, button: discord.ui.Button): await self._update(interaction, await get_system_embed(self.ctx.guild, self.lang), 1)
    @discord.ui.button(style=discord.ButtonStyle.secondary)
    async def btn_memory(self, interaction: discord.Interaction, button: discord.ui.Button): await self._update(interaction, await get_memory_embed(self.lang), 2)
    @discord.ui.button(style=discord.ButtonStyle.secondary)
    async def btn_config(self, interaction: discord.Interaction, button: discord.ui.Button): await self._update(interaction, await get_config_embed(self.lang), 3)
    @discord.ui.button(style=discord.ButtonStyle.success, row=1, emoji="📈")
    async def btn_monitor(self, interaction: discord.Interaction, button: discord.ui.Button):
        if tracemalloc.is_tracing():
            tracemalloc.stop()
            button.label, button.style = "Iniciar Monitor", discord.ButtonStyle.success
        else:
            tracemalloc.start()
            button.label, button.style = "Detener Monitor", discord.ButtonStyle.danger
            self.bot.loop.create_task(self._monitor_loop())
        await interaction.response.edit_message(view=self)