import logging
import asyncio
import os
import sys
import discord
from services.core import db_service
from services.core import lang_service
from ui import developer_ui

logger = logging.getLogger(__name__)

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

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

async def add_bot_status(tipo: str, texto: str, author_name: str):
    """Añade un nuevo estado a la base de datos."""
    await db_service.execute("INSERT INTO bot_statuses (type, text) VALUES (?, ?)", (tipo, texto))
    logger.info(f"Status agregado: [{tipo}] {texto} por {author_name}")

async def delete_bot_status(status_id: int, author_name: str):
    """Elimina un estado de la base de datos."""
    await db_service.execute("DELETE FROM bot_statuses WHERE id = ?", (status_id,))
    logger.info(f"Status eliminado (ID: {status_id}) por {author_name}")

async def perform_db_maintenance():
    """Ejecuta el comando VACUUM en la base de datos."""
    await db_service.execute("VACUUM;")

async def sync_commands(bot: discord.Client):
    """Sincroniza los comandos de aplicación del bot."""
    return await bot.tree.sync()

async def restart_bot(author_name: str):
    """Cierra la base de datos y reinicia el proceso del bot."""
    logger.info(f"🔄 [Developer] Reinicio solicitado por {author_name}")
    await db_service.close_db()
    os.execv(sys.executable, [sys.executable] + sys.argv)

async def handle_list_statuses(lang: str):
    """Obtiene el embed con la lista de estados."""
    return await developer_ui.get_status_list_embed(lang)

async def handle_add_status(tipo: str, texto: str, author_name: str, lang: str):
    """Añade un estado y retorna el embed de éxito."""
    await add_bot_status(tipo, texto, author_name)
    return developer_ui.get_status_add_success_embed(lang, texto, tipo)

async def handle_delete_status_prompt(lang: str):
    """Obtiene la vista y el placeholder para el menú de eliminación."""
    options = await developer_ui.get_status_delete_options(lang)
    if not options:
        return None, None
    ph = lang_service.get_text("status_placeholder", lang)
    view = developer_ui.StatusDeleteView(options, ph)
    return view, ph

async def handle_list_servers(bot, lang: str):
    """Obtiene las páginas de la lista de servidores."""
    return developer_ui.get_server_list_chunks(bot, lang)

async def handle_sync(bot, lang: str):
    """Sincroniza comandos y retorna el mensaje de resultado."""
    try:
        synced = await sync_commands(bot)
        return lang_service.get_text("dev_sync_success", lang, count=len(synced)), None
    except Exception as e:
        return None, lang_service.get_text("dev_sync_error", lang, error=e)

async def handle_bot_info(ctx, bot, lang: str):
    """Obtiene el embed inicial y la vista para el panel de información."""
    info = await get_psutil_info()
    embed = await developer_ui.get_general_embed(bot, ctx.guild, lang, info)
    view = developer_ui.BotInfoView(ctx, bot, lang)
    return embed, view

async def handle_db_maintenance(lang: str):
    """Ejecuta mantenimiento y retorna el embed de éxito."""
    await perform_db_maintenance()
    return developer_ui.get_db_maint_success_embed(lang)