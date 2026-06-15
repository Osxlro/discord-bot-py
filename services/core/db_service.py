import logging
import os
import asyncio
import sqlite3
import aiosqlite
import random
from config import settings

# --- CONFIGURACIÓN ---
logger = logging.getLogger(__name__)

DATA_DIR = os.path.join(settings.BASE_DIR, settings.DB_CONFIG["DIR_NAME"])
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

DB_NAME = settings.DB_CONFIG["FILE_NAME"]
DB_PATH = os.path.join(DATA_DIR, DB_NAME)
_connection = None

# --- CACHÉS EN MEMORIA ---
# _xp_cache: Write-behind (Escritura diferida). Se guarda en RAM y se vuelca a DB cada X tiempo.
# _config_cache: Read-through (Lectura a través). Se lee de DB si no está en RAM.
_xp_cache = {}      
_config_cache = {}  
_prefix_cache = {} # Caché para prefijos de usuario

# --- PROTOCOLO DE LIMPIEZA ---
# Solo las tablas en esta lista serán preservadas. 
# Cualquier otra tabla encontrada será eliminada para evitar basura.
REQUIRED_TABLES = {
    "users", "guild_stats", "guild_config", 
    "bot_persistence", "bot_statuses", "sqlite_sequence", "warns", "stream_alerts"
}

# =============================================================================
# 1. GESTIÓN DE CONEXIÓN Y BASE DE DATOS
# =============================================================================

async def get_db() -> aiosqlite.Connection:
    """Obtiene o crea la conexión a la base de datos."""
    global _connection
    if _connection is None:
        _connection = await aiosqlite.connect(DB_PATH)
        _connection.row_factory = aiosqlite.Row
    return _connection

async def close_db():
    """Cierra la conexión de forma segura, guardando datos pendientes."""
    global _connection
    try:
        await flush_xp_cache() # Guardar XP pendiente antes de cerrar
        if _connection:
            await _connection.close()
            logger.info("💾 Base de datos cerrada correctamente.")
            _connection = None
    except Exception:
        logger.exception("❌ Error cerrando base de datos")

async def init_db():
    """Inicializa la base de datos, tablas y migraciones."""
    db = await get_db()
    
    # --- OPTIMIZACIÓN: MODO WAL (Más velocidad y concurrencia) ---
    # WAL permite que las lecturas no bloqueen las escrituras y viceversa.
    await db.execute("PRAGMA journal_mode=WAL;") 
    await db.execute("PRAGMA synchronous=NORMAL;")
    await db.execute("PRAGMA temp_store=MEMORY;") # Operaciones temporales en RAM
    await db.execute("PRAGMA foreign_keys=ON;") # Asegurar integridad referencial
    await db.execute("PRAGMA mmap_size=268435456;")  # 256MB de Memory Mapping
    await db.execute("PRAGMA cache_size=-64000;")    # 64MB de cache
    await db.execute("PRAGMA busy_timeout=5000;")    # 5s de espera automática en bloqueos
    
    # --- DEFINICIÓN DE TABLAS ---
    
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
        coins INTEGER DEFAULT 0
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
        festivedays_enabled INTEGER DEFAULT 0,
        festivedays_channel_id INTEGER DEFAULT 0,
        festivedays_role_id INTEGER DEFAULT 0,
        language TEXT DEFAULT 'es'
    )
    """)

    # 6. Persistencia Genérica del Bot (Binary Store) - Definición robusta inicial
    await db.execute("""
    CREATE TABLE IF NOT EXISTS bot_persistence (
        namespace TEXT,
        key TEXT,
        data BLOB,
        created_at DATETIME DEFAULT (datetime('now')),
        PRIMARY KEY (namespace, key)
    )
    """)

    # Migración segura: SQLite no permite CURRENT_TIMESTAMP en ALTER TABLE ADD COLUMN
    await _ensure_column("bot_persistence", "created_at", "DATETIME DEFAULT (datetime('now'))")

    # 4. Estados Rotativos del Bot
    await db.execute("""
    CREATE TABLE IF NOT EXISTS bot_statuses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        type TEXT DEFAULT 'playing',
        text TEXT
    )
    """)
    
    # 7. Advertencias (Warns)
    await db.execute("""
    CREATE TABLE IF NOT EXISTS warns (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        guild_id INTEGER,
        user_id INTEGER,
        mod_id INTEGER,
        reason TEXT,
        timestamp DATETIME DEFAULT (datetime('now'))
    )
    """)

    # 8. Alertas de Stream (YouTube)
    await db.execute("""
    CREATE TABLE IF NOT EXISTS stream_alerts (
        guild_id INTEGER,
        platform TEXT,
        channel_name TEXT,
        discord_channel_id INTEGER,
        role_id INTEGER DEFAULT 0,
        last_status TEXT DEFAULT NULL,
        last_check DATETIME DEFAULT (datetime('now')),
        PRIMARY KEY (guild_id, platform, channel_name)
    )
    """)
    
    # --- ÍNDICES Y MIGRACIONES ---
    
    # Índice para leaderboard rápido
    await db.execute("CREATE INDEX IF NOT EXISTS idx_ranking ON guild_stats(guild_id, rebirths DESC, level DESC, xp DESC)")
    
    # --- MIGRACIONES ROBUSTAS ---
    await _ensure_column("users", "coins", "INTEGER DEFAULT 0")
    await _ensure_column("guild_stats", "rebirths", "INTEGER DEFAULT 0")
    await _ensure_column("guild_config", "language", "TEXT DEFAULT 'es'")
    await _ensure_column("guild_config", "server_goodbye_msg", "TEXT DEFAULT NULL")
    await _ensure_column("guild_config", "minecraft_channel_id", "INTEGER DEFAULT 0")
    await _ensure_column("guild_config", "wordday_channel_id", "INTEGER DEFAULT 0")
    await _ensure_column("guild_config", "wordday_role_id", "INTEGER DEFAULT 0")
    await _ensure_column("guild_config", "festivedays_enabled", "INTEGER DEFAULT 0")
    await _ensure_column("guild_config", "festivedays_channel_id", "INTEGER DEFAULT 0")
    await _ensure_column("guild_config", "festivedays_role_id", "INTEGER DEFAULT 0")
    await _ensure_column("stream_alerts", "guild_id", "INTEGER")
    await _ensure_column("stream_alerts", "platform", "TEXT")
    await _ensure_column("stream_alerts", "channel_name", "TEXT")
    await _ensure_column("stream_alerts", "discord_channel_id", "INTEGER")
    await _ensure_column("stream_alerts", "role_id", "INTEGER DEFAULT 0")
    await _ensure_column("stream_alerts", "last_status", "TEXT DEFAULT NULL")
    await _ensure_column("stream_alerts", "last_check", "DATETIME DEFAULT (datetime('now'))")

    # --- PROTOCOLO DE LIMPIEZA Y OPTIMIZACIÓN ---
    await _cleanup_unused_tables()
    await db.commit()
    
    logger.info("💾 Base de datos inicializada.")

async def _ensure_column(table: str, column: str, definition: str):
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

async def _cleanup_unused_tables():
    """Detecta y elimina tablas que ya no son utilizadas por el bot."""
    db = await get_db()
    async with db.execute("SELECT name FROM sqlite_master WHERE type='table'") as cursor:
        existing_tables = [row['name'] for row in await cursor.fetchall()]
    
    for table in existing_tables:
        if table not in REQUIRED_TABLES and not table.startswith("sqlite_"):
            # Seguridad: Solo alertar en logs en lugar de borrar datos automáticamente
            logger.warning(f"⚠️ [DB Service] Tabla detectada fuera de esquema: '{table}'. No se eliminará automáticamente.")

# =============================================================================
# 2. HELPERS DE CONSULTA (CORE)
# =============================================================================

async def execute(query: str, params: tuple = ()):
    """Ejecuta una consulta de escritura (INSERT, UPDATE, DELETE)."""
    async def _op():
        db = await get_db()
        await db.execute(query, params)
        await db.commit()
    await _execute_with_retry(_op)

async def fetch_one(query: str, params: tuple = ()):
    """Ejecuta una consulta de lectura y retorna un solo resultado."""
    async def _op():
        db = await get_db()
        async with db.execute(query, params) as c: 
            return await c.fetchone()
    return await _execute_with_retry(_op)

async def fetch_all(query: str, params: tuple = ()):
    """Ejecuta una consulta de lectura y retorna todos los resultados."""
    async def _op():
        db = await get_db()
        async with db.execute(query, params) as c: 
            return await c.fetchall()
    return await _execute_with_retry(_op)

# =============================================================================
# 3. GESTIÓN DE CACHÉ Y MEMORIA
# =============================================================================

def clear_memory_cache():
    """Limpia el caché de configuración de la RAM para liberar memoria."""
    global _config_cache
    _prefix_cache.clear()
    _config_cache.clear()
    # Nota: No limpiamos _xp_cache aquí porque puede tener datos sin guardar.

def clear_xp_cache_safe():
    """
    Limpia entradas de XP en memoria que ya han sido guardadas en DB.
    Esto previene que el diccionario crezca infinitamente (Memory Leak).
    """
    global _xp_cache
    # Solo eliminamos las entradas que NO tienen cambios pendientes ('dirty': False)
    keys_to_remove = [k for k, v in _xp_cache.items() if not v['dirty']]
    
    for k in keys_to_remove:
        del _xp_cache[k]

async def _execute_with_retry(func, *args, **kwargs):
    """
    Wrapper para reintentar operaciones de DB si está bloqueada (SQLite Locked).
    """
    retries = settings.DB_CONFIG["RETRIES"]
    base_delay = settings.DB_CONFIG["RETRY_DELAY"]
    
    for i in range(retries):
        try:
            return await func(*args, **kwargs)
        except sqlite3.OperationalError as e:
            # Si la base de datos está bloqueada, esperamos y reintentamos
            if "locked" in str(e) and i < retries - 1:
                await asyncio.sleep(base_delay * (i + 1))
                continue
            raise e
        except Exception as e:
            raise e

async def flush_xp_cache():
    """Vuelca los datos de XP acumulados en RAM hacia la base de datos."""
    if not _xp_cache: return
    
    updates = []
    # Recolectamos solo los datos "sucios" (modificados)
    # Esto reduce la carga de trabajo al procesar solo lo que realmente cambió.
    pending_clean = {} # Usamos un dict para guardar el snapshot de XP
    for key, data in list(_xp_cache.items()): # Iteramos sobre una copia para seguridad
        if data['dirty']:
            updates.append((data['xp'], data['level'], data['rebirths'], key[0], key[1]))
            pending_clean[key] = data['xp'] # Guardamos la XP exacta que estamos enviando a DB
    
    if updates:
        try:
            async def _do_update():
                db = await get_db()
                await db.execute("BEGIN TRANSACTION;")
                try:
                    await db.executemany("""
                        INSERT INTO guild_stats (xp, level, rebirths, guild_id, user_id) 
                        VALUES (?, ?, ?, ?, ?)
                        ON CONFLICT(guild_id, user_id) DO UPDATE SET 
                        xp = excluded.xp, level = excluded.level, rebirths = excluded.rebirths
                    """, updates)
                    await db.execute("COMMIT;")
                except Exception as e:
                    await db.execute("ROLLBACK;")
                    raise e

            await _execute_with_retry(_do_update)
            
            # CRÍTICO: Solo marcamos como limpios si la DB confirmó el guardado
            # Y si la XP no ha cambiado mientras esperábamos (Race Condition fix)
            for key, saved_xp in pending_clean.items():
                if key in _xp_cache:
                    if _xp_cache[key]['xp'] == saved_xp:
                        _xp_cache[key]['dirty'] = False
            
            # Limpieza de memoria para evitar leaks (Memory Leak Fix)
            clear_xp_cache_safe()
        except Exception:
            logger.exception("⚠️ Error guardando caché de XP")

# =============================================================================
# 4. LÓGICA DE NEGOCIO: CONFIGURACIÓN (GUILD CONFIG)
# =============================================================================

async def prune_old_persistence(days: int = 7):
    """Elimina datos de persistencia más antiguos que X días."""
    await execute("DELETE FROM bot_persistence WHERE created_at < datetime('now', ?) OR created_at IS NULL", (f'-{days} days',))
    logger.debug(f"🧹 [DB Service] Persistencia antigua eliminada ({days} días).")

async def get_persistence_stats() -> dict:
    """Obtiene estadísticas de uso de la tabla de persistencia."""
    row = await fetch_one("SELECT COUNT(*) as count, SUM(LENGTH(data)) as size FROM bot_persistence")
    return {"count": row['count'] or 0, "size_kb": (row['size'] or 0) / 1024}

async def get_guild_config(guild_id: int) -> dict:
    """
    Obtiene la configuración de un servidor.
    Usa caché en RAM para evitar lecturas constantes a disco.
    """
    if guild_id in _config_cache:
        return _config_cache[guild_id].copy() # Retornamos copia para evitar mutación del caché

    row = await fetch_one("SELECT * FROM guild_config WHERE guild_id = ?", (guild_id,))
    
    if row:
        config = dict(row)
    else:
        # Valores por defecto si no existe configuración
        config = settings.DEFAULT_GUILD_CONFIG.copy()
        config["guild_id"] = guild_id
    
    _config_cache[guild_id] = config
    return config.copy()

async def update_guild_config(guild_id: int, updates: dict):
    """Actualiza la configuración en DB y refresca el CACHÉ."""
    # 1. Actualizar DB usando UPSERT (Sintaxis más eficiente)
    cols = ", ".join(["guild_id"] + list(updates.keys()))
    placeholders = ", ".join(["?"] * (len(updates) + 1))
    set_clause = ", ".join([f"{k} = excluded.{k}" for k in updates.keys()])
    values = [guild_id] + list(updates.values())

    await execute(f"""
        INSERT INTO guild_config ({cols}) VALUES ({placeholders})
        ON CONFLICT(guild_id) DO UPDATE SET {set_clause}
    """, tuple(values))

    # 2. Actualizar Caché
    if guild_id not in _config_cache:
        await get_guild_config(guild_id)
    else:
        _config_cache[guild_id].update(updates)

async def get_user_prefix(user_id: int) -> str | None:
    """
    Obtiene el prefijo personalizado de un usuario usando caché.
    """
    if user_id in _prefix_cache:
        return _prefix_cache[user_id]

    row = await fetch_one("SELECT custom_prefix FROM users WHERE user_id = ?", (user_id,))
    prefix = row['custom_prefix'] if row else None
    
    # Guardamos en caché (incluso si es None, para evitar re-consultar que no tiene)
    _prefix_cache[user_id] = prefix
    return prefix

async def get_user_coins(user_id: int) -> int:
    """Obtiene la cantidad de monedas de un usuario (global)."""
    row = await fetch_one("SELECT coins FROM users WHERE user_id = ?", (user_id,))
    return row['coins'] if row else 0

async def add_user_coins(user_id: int, amount: int):
    """Añade o quita monedas a un usuario (global)."""
    await execute("""
        INSERT INTO users (user_id, coins) VALUES (?, ?)
        ON CONFLICT(user_id) DO UPDATE SET coins = coins + excluded.coins
    """, (user_id, amount))

# =============================================================================
# 5. LÓGICA DE NEGOCIO: XP Y NIVELES
# =============================================================================

def calculate_xp_required(level: int) -> int:
    """Calcula la XP necesaria para alcanzar el siguiente nivel."""
    return int(settings.LEVELS_CONFIG["XP_MULTIPLIER"] * (level ** settings.LEVELS_CONFIG["XP_EXPONENT"]))

async def add_xp(guild_id: int, user_id: int, amount: int) -> tuple[int, bool]:
    """
    Añade XP a un usuario en memoria (Write-behind).
    Retorna: (Nuevo Nivel, ¿Subió de nivel?)
    """
    key = (guild_id, user_id)
    
    # Si no está en caché, cargamos de DB o inicializamos
    if key not in _xp_cache:
        row = await fetch_one("SELECT xp, level, rebirths FROM guild_stats WHERE guild_id = ? AND user_id = ?", (guild_id, user_id))
        if row:
            _xp_cache[key] = {'xp': row['xp'], 'level': row['level'], 'rebirths': row['rebirths'], 'dirty': False}
        else:
            _xp_cache[key] = {'xp': 0, 'level': 1, 'rebirths': 0, 'dirty': False}
    
    data = _xp_cache[key]
    data['xp'] += amount
    data['dirty'] = True 
    
    required = calculate_xp_required(data['level'])
    leveled_up = False
    
    while data['xp'] >= required:
        data['xp'] -= required
        data['level'] += 1
        leveled_up = True
        
        # Otorgar monedas por cada nivel subido
        coins_min, coins_max = settings.LEVELS_CONFIG.get("COINS_PER_LEVEL", (5, 10))
        coins_earned = random.randint(coins_min, coins_max)
        await add_user_coins(user_id, coins_earned)
        
        required = calculate_xp_required(data['level'])
    
    return data['level'], leveled_up

async def do_rebirth(guild_id: int, user_id: int) -> tuple[bool, any]:
    """
    Realiza un renacimiento si el usuario es nivel 100+.
    Retorna: (Éxito, Nuevo conteo de Rebirths o Error)
    """
    # Forzamos guardado de caché para asegurar consistencia
    await flush_xp_cache()
    
    row = await fetch_one("SELECT level, rebirths FROM guild_stats WHERE guild_id = ? AND user_id = ?", (guild_id, user_id))
    
    if not row: return False, "no_data"
    min_level = settings.LEVELS_CONFIG["REBIRTH_LEVEL"]
    if row['level'] < min_level: return False, row['level']
    
    # Verificar si el usuario tiene suficientes monedas
    cost = settings.LEVELS_CONFIG.get("REBIRTH_COST", 100)
    coins = await get_user_coins(user_id)
    if coins < cost:
        return False, "not_enough_coins"
    
    new_reb = row['rebirths'] + 1
    
    # Deducir monedas
    await add_user_coins(user_id, -cost)
    
    # Actualizamos DB directamente
    await execute("UPDATE guild_stats SET level = 1, xp = 0, rebirths = ? WHERE guild_id = ? AND user_id = ?", (new_reb, guild_id, user_id))
    
    # Actualizamos caché si existe
    key = (guild_id, user_id)
    if key in _xp_cache:
        _xp_cache[key].update({'level': 1, 'xp': 0, 'rebirths': new_reb, 'dirty': False})
        
    return True, new_reb
