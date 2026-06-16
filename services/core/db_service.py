import logging
import asyncio
from config import settings
from services.core import database
from services.repositories.config_repository import ConfigRepository
from services.repositories.xp_repository import XpRepository, calculate_xp_required
from services.repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)

# Re-exportar funciones y variables basales para retrocompatibilidad
get_db = database.get_db
execute = database.execute
fetch_one = database.fetch_one
fetch_all = database.fetch_all
DB_PATH = database.DB_PATH

REQUIRED_TABLES = {
    "users", "guild_stats", "guild_config", "bot_persistence",
    "bot_statuses", "warns", "stream_alerts"
}

async def _ensure_column(table: str, column: str, definition: str):
    """Verifica si una columna existe en la tabla y si no, la crea."""
    await database.ensure_column(table, column, definition)

from services.repositories.xp_repository import _xp_cache

async def close_db():
    """Cierra la conexión de forma segura, volcando caché primero."""
    try:
        await flush_xp_cache()
    finally:
        await database.close_db()

async def init_db():
    """Inicializa la estructura de base de datos, tablas y migraciones."""
    await database.init_db_structure()
    db = await database.get_db()
    
    # 1. Usuarios (Preferencias globales)
    await db.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        birthday TEXT DEFAULT NULL,
        celebrate BOOLEAN DEFAULT 1,
        custom_prefix TEXT DEFAULT NULL,
        description TEXT DEFAULT 'Sin descripción.',
        personal_level_msg TEXT DEFAULT NULL,
        personal_birthday_msg TEXT DEFAULT NULL,
        coins INTEGER DEFAULT 0,
        gender TEXT DEFAULT NULL
    )
    """)
    
    # 2. Estadísticas por Servidor (XP, Niveles, Rebirths)
    await db.execute("""
    CREATE TABLE IF NOT EXISTS guild_stats (
        guild_id INTEGER,
        user_id INTEGER,
        rebirths INTEGER DEFAULT 0,
        xp INTEGER DEFAULT 0,
        level INTEGER DEFAULT 1,
        PRIMARY KEY (guild_id, user_id)
    )
    """)
    
    # Crear índice para optimizar leaderboard si no existe
    await db.execute("CREATE INDEX IF NOT EXISTS idx_ranking ON guild_stats (guild_id, rebirths DESC, level DESC, xp DESC)")

    # 3. Configuración del Servidor
    await db.execute("""
    CREATE TABLE IF NOT EXISTS guild_config (
        guild_id INTEGER PRIMARY KEY,
        chaos_enabled BOOLEAN DEFAULT 1,
        chaos_probability REAL DEFAULT 0.01,
        welcome_channel_id INTEGER DEFAULT 0,
        confessions_channel_id INTEGER DEFAULT 0,
        logs_channel_id INTEGER DEFAULT 0,
        birthday_channel_id INTEGER DEFAULT 0,
        autorole_id INTEGER DEFAULT 0,
        mention_response TEXT DEFAULT NULL,
        server_level_msg TEXT DEFAULT NULL,
        server_birthday_msg TEXT DEFAULT NULL,
        server_kick_msg TEXT DEFAULT NULL,
        server_ban_msg TEXT DEFAULT NULL,
        server_goodbye_msg TEXT DEFAULT NULL,
        minecraft_channel_id INTEGER DEFAULT 0,
        wordday_channel_id INTEGER DEFAULT 0,
        wordday_role_id INTEGER DEFAULT 0,
        language TEXT DEFAULT 'es',
        festivedays_enabled BOOLEAN DEFAULT 0,
        festivedays_channel_id INTEGER DEFAULT 0,
        festivedays_role_id INTEGER DEFAULT 0
    )
    """)

    # 4. Persistencia Binaria Genérica
    await db.execute("""
    CREATE TABLE IF NOT EXISTS bot_persistence (
        namespace TEXT,
        key TEXT,
        data BLOB,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (namespace, key)
    )
    """)

    # 5. Estados Rotativos del Bot
    await db.execute("""
    CREATE TABLE IF NOT EXISTS bot_statuses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        type TEXT DEFAULT 'playing',
        text TEXT
    )
    """)

    # 6. Registro de Advertencias (Warns)
    await db.execute("""
    CREATE TABLE IF NOT EXISTS warns (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        guild_id INTEGER,
        user_id INTEGER,
        mod_id INTEGER,
        reason TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # 7. Alertas de Stream (YouTube / Twitch)
    await db.execute("""
    CREATE TABLE IF NOT EXISTS stream_alerts (
        guild_id INTEGER,
        platform TEXT,
        channel_name TEXT,
        discord_channel_id INTEGER,
        role_id INTEGER DEFAULT 0,
        custom_message TEXT DEFAULT NULL,
        last_status TEXT DEFAULT NULL,
        last_check DATETIME DEFAULT (datetime('now')),
        PRIMARY KEY (guild_id, platform, channel_name)
    )
    """)

    # --- MIGRACIONES DE COLUMNAS (Asegura consistencia estructural en actualizaciones) ---
    await _ensure_column("users", "coins", "INTEGER DEFAULT 0")
    await _ensure_column("users", "gender", "TEXT DEFAULT NULL")
    
    await _ensure_column("guild_stats", "rebirths", "INTEGER DEFAULT 0")
    
    await _ensure_column("guild_config", "server_goodbye_msg", "TEXT DEFAULT NULL")
    await _ensure_column("guild_config", "minecraft_channel_id", "INTEGER DEFAULT 0")
    await _ensure_column("guild_config", "wordday_channel_id", "INTEGER DEFAULT 0")
    await _ensure_column("guild_config", "wordday_role_id", "INTEGER DEFAULT 0")
    await _ensure_column("guild_config", "language", "TEXT DEFAULT 'es'")
    
    await _ensure_column("guild_config", "festivedays_enabled", "BOOLEAN DEFAULT 0")
    await _ensure_column("guild_config", "festivedays_channel_id", "INTEGER DEFAULT 0")
    await _ensure_column("guild_config", "festivedays_role_id", "INTEGER DEFAULT 0")
    
    await _ensure_column("bot_persistence", "created_at", "DATETIME DEFAULT CURRENT_TIMESTAMP")
    
    await _ensure_column("stream_alerts", "guild_id", "INTEGER")
    await _ensure_column("stream_alerts", "platform", "TEXT")
    await _ensure_column("stream_alerts", "channel_name", "TEXT")
    await _ensure_column("stream_alerts", "discord_channel_id", "INTEGER")
    await _ensure_column("stream_alerts", "role_id", "INTEGER DEFAULT 0")
    await _ensure_column("stream_alerts", "custom_message", "TEXT DEFAULT NULL")
    await _ensure_column("stream_alerts", "last_status", "TEXT DEFAULT NULL")
    await _ensure_column("stream_alerts", "last_check", "DATETIME DEFAULT (datetime('now'))")

    await database.cleanup_unused_tables()
    await db.commit()
    logger.info("💾 Base de datos inicializada correctamente.")

# --- DELEGACIÓN DE MÉTODOS DE REPOSITORIO ---

async def get_guild_config(guild_id: int) -> dict:
    return await ConfigRepository.get_guild_config(guild_id)

async def update_guild_config(guild_id: int, updates: dict):
    await ConfigRepository.update_guild_config(guild_id, updates)

async def get_user_prefix(user_id: int) -> str | None:
    return await UserRepository.get_user_prefix(user_id)

async def set_user_prefix(user_id: int, prefix: str | None):
    await UserRepository.set_user_prefix(user_id, prefix)

async def get_user_coins(user_id: int) -> int:
    return await UserRepository.get_user_coins(user_id)

async def add_user_coins(user_id: int, amount: int):
    await UserRepository.add_user_coins(user_id, amount)

async def set_user_coins(user_id: int, amount: int):
    await UserRepository.set_user_coins(user_id, amount)

async def add_xp(guild_id: int, user_id: int, amount: int) -> tuple[int, bool]:
    return await XpRepository.add_xp(guild_id, user_id, amount)

async def set_user_xp_level(guild_id: int, user_id: int, xp: int, level: int, rebirths: int = None):
    await XpRepository.set_user_xp_level(guild_id, user_id, xp, level, rebirths)

async def do_rebirth(guild_id: int, user_id: int) -> tuple[bool, any]:
    return await XpRepository.do_rebirth(guild_id, user_id)

async def flush_xp_cache():
    await XpRepository.flush_xp_cache()

def clear_memory_cache():
    """Limpia el caché de configuración de la RAM para liberar memoria."""
    from services.core.cache_service import cache
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(cache.clear())
    except RuntimeError:
        asyncio.run(cache.clear())

async def prune_old_persistence(days: int = 7):
    """Elimina datos de persistencia más antiguos que X días."""
    await database.execute("DELETE FROM bot_persistence WHERE created_at < datetime('now', ?) OR created_at IS NULL", (f'-{days} days',))
    logger.info(f"🧹 [DB Service] Persistencia antigua eliminada ({days} días).")

async def get_persistence_stats() -> dict:
    """Obtiene estadísticas de uso de la tabla de persistencia."""
    row = await database.fetch_one("SELECT COUNT(*) as count, SUM(LENGTH(data)) as size FROM bot_persistence")
    return {"count": row['count'] or 0, "size_kb": (row['size'] or 0) / 1024 if row and row['size'] else 0}

def clear_xp_cache_safe():
    """Limpia entradas de XP en memoria sin cambios pendientes para evitar fugas de memoria."""
    XpRepository.clear_xp_cache_safe()
