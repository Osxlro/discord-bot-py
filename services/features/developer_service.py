import logging
import asyncio
import os
import sys
import discord
from services.core import db_service

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