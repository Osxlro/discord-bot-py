import logging
import asyncio
import os
import tracemalloc
import platform
import sys
import time
import discord
from services.core import lang_service
from config import settings
from services.core import db_service

logger = logging.getLogger(__name__)

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

def _make_bar(percent, length=settings.UI_CONFIG["BAR_LENGTH"]):
    filled = int(length * percent / 100)
    return "█" * filled + "░" * (length - filled)

def _get_psutil_info_sync():
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

async def get_psutil_info():
    return await asyncio.to_thread(_get_psutil_info_sync)

async def get_general_embed(bot, guild, lang):
    info = await get_psutil_info()
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

async def get_system_embed(guild, lang):
    info = await get_psutil_info()
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

async def get_memory_embed(lang):
    embed = discord.Embed(title=lang_service.get_text("botinfo_memory_title", lang), color=settings.COLORS["GOLD"])
    if not tracemalloc.is_tracing():
        embed.description = lang_service.get_text("dev_mem_nodetail", lang)
        info = await get_psutil_info()
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
        name="💾 Persistencia Binaria", 
        value=f"• Registros: `{p_stats['count']}`\n• Tamaño: `{p_stats['size_kb']:.2f} KB`", 
        inline=False
    )

    rows = await db_service.fetch_all("SELECT type, text FROM bot_statuses")
    status_txt = "\n".join([f"• [{r['type']}] {r['text']}" for r in rows[:5]]) + (f"\n... y {len(rows)-5} más." if len(rows) > 5 else "") if rows else lang_service.get_text("log_none", lang)
    embed.add_field(name=lang_service.get_text("botinfo_statuses", lang), value=status_txt, inline=False)
    return embed

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

async def get_memory_analysis(lang):
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
    return desc