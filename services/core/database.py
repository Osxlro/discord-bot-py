import logging
import os
import asyncio
import sqlite3
import aiosqlite
from config import settings

logger = logging.getLogger(__name__)

DATA_DIR = os.path.join(settings.BASE_DIR, settings.DB_CONFIG["DIR_NAME"])
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

DB_NAME = settings.DB_CONFIG["FILE_NAME"]
DB_PATH = os.path.join(DATA_DIR, DB_NAME)
_connection = None

REQUIRED_TABLES = {
    "users", "guild_stats", "guild_config", 
    "bot_persistence", "bot_statuses", "sqlite_sequence", "warns", "stream_alerts",
    "user_inventory", "shop_items"
}

async def get_db() -> aiosqlite.Connection:
    """Obtiene o crea la conexión a la base de datos."""
    global _connection
    if _connection is None:
        _connection = await aiosqlite.connect(DB_PATH)
        _connection.row_factory = aiosqlite.Row
    return _connection

async def close_db():
    """Cierra la conexión a la base de datos de forma segura."""
    global _connection
    try:
        if _connection:
            await _connection.close()
            logger.info("💾 Conexión física a la base de datos cerrada.")
            _connection = None
    except Exception:
        logger.exception("❌ Error cerrando conexión física de base de datos")

async def init_db_structure():
    """Inicializa la base de datos y la configuración del modo WAL."""
    db = await get_db()
    await db.execute("PRAGMA journal_mode=WAL;") 
    await db.execute("PRAGMA synchronous=NORMAL;")
    await db.execute("PRAGMA temp_store=MEMORY;")
    await db.execute("PRAGMA foreign_keys=ON;")
    await db.execute("PRAGMA mmap_size=268435456;")
    await db.execute("PRAGMA cache_size=-64000;")
    await db.execute("PRAGMA busy_timeout=5000;")

async def ensure_column(table: str, column: str, definition: str):
    """Verifica si una columna existe y si no, la crea."""
    db = await get_db()
    async with db.execute(f"PRAGMA table_info({table})") as cursor:
        columns = [row['name'] for row in await cursor.fetchall()]
        if column not in columns:
            try:
                await db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
                await db.commit()
                logger.info(f"🛠️ Columna '{column}' añadida a la tabla '{table}'.")
            except Exception:
                logger.exception(f"❌ Error en migración {table}.{column}")

async def cleanup_unused_tables():
    """Detecta y alerta sobre tablas que ya no son utilizadas por el bot."""
    db = await get_db()
    async with db.execute("SELECT name FROM sqlite_master WHERE type='table'") as cursor:
        existing_tables = [row['name'] for row in await cursor.fetchall()]
    
    for table in existing_tables:
        if table not in REQUIRED_TABLES and not table.startswith("sqlite_"):
            logger.warning(f"⚠️ [DB Service] Tabla detectada fuera de esquema: '{table}'. No se eliminará automáticamente.")

async def execute(query: str, params: tuple = ()):
    """Ejecuta una consulta de escritura (INSERT, UPDATE, DELETE)."""
    async def _op():
        db = await get_db()
        await db.execute(query, params)
        await db.commit()
    await execute_with_retry(_op)

async def fetch_one(query: str, params: tuple = ()):
    """Ejecuta una consulta de lectura y retorna un solo resultado."""
    async def _op():
        db = await get_db()
        async with db.execute(query, params) as c: 
            return await c.fetchone()
    return await execute_with_retry(_op)

async def fetch_all(query: str, params: tuple = ()):
    """Ejecuta una consulta de lectura y retorna todos los resultados."""
    async def _op():
        db = await get_db()
        async with db.execute(query, params) as c: 
            return await c.fetchall()
    return await execute_with_retry(_op)

async def execute_with_retry(func, *args, **kwargs):
    """Wrapper para reintentar operaciones si SQLite está bloqueada."""
    retries = settings.DB_CONFIG["RETRIES"]
    base_delay = settings.DB_CONFIG["RETRY_DELAY"]
    
    for i in range(retries):
        try:
            return await func(*args, **kwargs)
        except sqlite3.OperationalError as e:
            if "locked" in str(e) and i < retries - 1:
                await asyncio.sleep(base_delay * (i + 1))
                continue
            raise e
        except Exception as e:
            raise e

async def execute_transaction(queries: list[tuple[str, tuple]]):
    """Ejecuta una lista de consultas (query, params) dentro de una única transacción atómica."""
    async def _op():
        db = await get_db()
        await db.execute("BEGIN TRANSACTION;")
        try:
            for query, params in queries:
                await db.execute(query, params)
            await db.commit()
        except Exception as e:
            await db.rollback()
            raise e
    await execute_with_retry(_op)
