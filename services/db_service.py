import aiosqlite
import os
import logging
from config import settings

# --- CONFIGURACIÓN ---
logger = logging.getLogger(__name__)

DATA_DIR = os.path.join(settings.BASE_DIR, "data")
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

DB_NAME = "database.sqlite3"
DB_PATH = os.path.join(DATA_DIR, DB_NAME)
_connection = None

# --- CACHÉS EN MEMORIA ---
# _xp_cache: Write-behind (Escritura diferida). Se guarda en RAM y se vuelca a DB cada X tiempo.
# _config_cache: Read-through (Lectura a través). Se lee de DB si no está en RAM.
_xp_cache = {}      
_config_cache = {}  

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
    except Exception as e:
        logger.error(f"❌ Error cerrando base de datos: {e}")

async def init_db():
    """Inicializa la base de datos, tablas y migraciones."""
    db = await get_db()
    
    # --- OPTIMIZACIÓN: MODO WAL (Más velocidad y concurrencia) ---
    await db.execute("PRAGMA journal_mode=WAL;")
    await db.execute("PRAGMA synchronous=NORMAL;")
    
    # Compactar base de datos al inicio para liberar espacio en disco
    await db.execute("VACUUM;")

    # --- DEFINICIÓN DE TABLAS ---
    
    # 1. Usuarios (Preferencias globales)
    await db.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        xp INTEGER DEFAULT 0,
        level INTEGER DEFAULT 1,
        birthday TEXT DEFAULT NULL,
        celebrate BOOLEAN DEFAULT 1,
        custom_prefix TEXT DEFAULT NULL,
        description TEXT DEFAULT 'Sin descripción.',
        personal_level_msg TEXT DEFAULT NULL,
        personal_birthday_msg TEXT DEFAULT NULL
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
        language TEXT DEFAULT 'es'
    )
    """)

    # 4. Estados Rotativos del Bot
    await db.execute("""
    CREATE TABLE IF NOT EXISTS bot_statuses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        type TEXT DEFAULT 'playing',
        text TEXT
    )
    """)
    
    # --- ÍNDICES Y MIGRACIONES ---
    
    # Índice para leaderboard rápido
    await db.execute("CREATE INDEX IF NOT EXISTS idx_ranking ON guild_stats(guild_id, rebirths DESC, level DESC, xp DESC)")
    
    # Migraciones silenciosas por si acaso
    migraciones = [
        "ALTER TABLE guild_stats ADD COLUMN rebirths INTEGER DEFAULT 0",
        "ALTER TABLE guild_config ADD COLUMN language TEXT DEFAULT 'es'"
    ]
    for q in migraciones:
        try: await db.execute(q)
        except: pass

    await db.commit()
    
    # Sugerencia de escalado: 
    # Si settings.REDIS_URL existe, inicializar cliente de Redis aquí
    # para mover _xp_cache y _config_cache fuera de la memoria local.
    logger.info("💾 Base de datos inicializada.")

# =============================================================================
# 2. HELPERS DE CONSULTA (CORE)
# =============================================================================

async def execute(query: str, params: tuple = ()):
    """Ejecuta una consulta de escritura (INSERT, UPDATE, DELETE)."""
    db = await get_db()
    await db.execute(query, params)
    await db.commit()

async def fetch_one(query: str, params: tuple = ()):
    """Ejecuta una consulta de lectura y retorna un solo resultado."""
    db = await get_db()
    async with db.execute(query, params) as c: 
        return await c.fetchone()

async def fetch_all(query: str, params: tuple = ()):
    """Ejecuta una consulta de lectura y retorna todos los resultados."""
    db = await get_db()
    async with db.execute(query, params) as c: 
        return await c.fetchall()

# =============================================================================
# 3. GESTIÓN DE CACHÉ Y MEMORIA
# =============================================================================

def clear_memory_cache():
    """Limpia el caché de configuración de la RAM para liberar memoria."""
    global _config_cache
    _config_cache.clear()
    # Nota: No limpiamos _xp_cache aquí porque puede tener datos sin guardar.

async def flush_xp_cache():
    """Vuelca los datos de XP acumulados en RAM hacia la base de datos."""
    if not _xp_cache: return
    
    updates = []
    # Recolectamos solo los datos "sucios" (modificados)
    for key, data in _xp_cache.items():
        if data['dirty']:
            updates.append((data['xp'], data['level'], data['rebirths'], key[0], key[1]))
            data['dirty'] = False
    
    if updates:
        try:
            db = await get_db()
            await db.executemany("""
                INSERT INTO guild_stats (xp, level, rebirths, guild_id, user_id) 
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(guild_id, user_id) DO UPDATE SET 
                xp = excluded.xp, level = excluded.level, rebirths = excluded.rebirths
            """, updates)
            await db.commit()
        except Exception as e:
            logger.error(f"⚠️ Error guardando caché de XP: {e}")

# =============================================================================
# 4. LÓGICA DE NEGOCIO: CONFIGURACIÓN (GUILD CONFIG)
# =============================================================================

async def get_guild_config(guild_id: int) -> dict:
    """
    Obtiene la configuración de un servidor.
    Usa caché en RAM para evitar lecturas constantes a disco.
    """
    if guild_id in _config_cache:
        return _config_cache[guild_id]

    row = await fetch_one("SELECT * FROM guild_config WHERE guild_id = ?", (guild_id,))
    
    if row:
        config = dict(row)
    else:
        # Valores por defecto si no existe configuración
        config = {
            "guild_id": guild_id,
            "language": "es",
            "chaos_enabled": 1,
            "chaos_probability": 0.01
        }
    
    _config_cache[guild_id] = config
    return config

async def update_guild_config(guild_id: int, updates: dict):
    """Actualiza la configuración en DB y refresca el CACHÉ."""
    # 1. Actualizar DB
    exists = await fetch_one("SELECT 1 FROM guild_config WHERE guild_id = ?", (guild_id,))
    
    if exists:
        set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
        values = list(updates.values()) + [guild_id]
        await execute(f"UPDATE guild_config SET {set_clause} WHERE guild_id = ?", values)
    else:
        cols = ", ".join(["guild_id"] + list(updates.keys()))
        placeholders = ", ".join(["?"] * (len(updates) + 1))
        values = [guild_id] + list(updates.values())
        await execute(f"INSERT INTO guild_config ({cols}) VALUES ({placeholders})", values)

    # 2. Actualizar Caché
    if guild_id not in _config_cache:
        await get_guild_config(guild_id)
    else:
        _config_cache[guild_id].update(updates)

# =============================================================================
# 5. LÓGICA DE NEGOCIO: XP Y NIVELES
# =============================================================================

def calculate_xp_required(level: int) -> int:
    """Calcula la XP necesaria para alcanzar el siguiente nivel."""
    return int(100 * (level ** 1.2))

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
    if row['level'] < 100: return False, row['level']
    
    new_reb = row['rebirths'] + 1
    
    # Actualizamos DB directamente
    await execute("UPDATE guild_stats SET level = 1, xp = 0, rebirths = ? WHERE guild_id = ? AND user_id = ?", (new_reb, guild_id, user_id))
    
    # Actualizamos caché si existe
    key = (guild_id, user_id)
    if key in _xp_cache:
        _xp_cache[key].update({'level': 1, 'xp': 0, 'rebirths': new_reb, 'dirty': False})
        
    return True, new_reb
