import aiosqlite
import os
from config import settings

DATA_DIR = os.path.join(settings.BASE_DIR, "data")
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

DB_NAME = "database.sqlite3"
DB_PATH = os.path.join(DATA_DIR, DB_NAME)
_connection = None

# --- CACHÉ EN MEMORIA (Optimización I/O) ---
# Estructura: {(guild_id, user_id): {'xp': 0, 'level': 1, 'rebirths': 0, 'dirty': False}}
_xp_cache = {}

async def get_db() -> aiosqlite.Connection:
    global _connection
    if _connection is None:
        _connection = await aiosqlite.connect(DB_PATH)
        _connection.row_factory = aiosqlite.Row
    return _connection

async def close_db():
    global _connection
    # Antes de cerrar, aseguramos guardar todo lo pendiente
    await flush_xp_cache()
    if _connection:
        await _connection.close()
        _connection = None

async def init_db():
    db = await get_db()
    
    # ... (Tablas users, guild_stats, guild_config, bot_statuses, chat_logs... MANTENER IGUAL) ...
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
    
    await db.execute("""
    CREATE TABLE IF NOT EXISTS guild_stats (
        guild_id INTEGER,
        user_id INTEGER,
        xp INTEGER DEFAULT 0,
        level INTEGER DEFAULT 1,
        rebirths INTEGER DEFAULT 0,
        PRIMARY KEY (guild_id, user_id)
    )
    """)
    
    # ... (Resto de tablas omitidas para brevedad, no las borres) ...
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

    await db.execute("""
    CREATE TABLE IF NOT EXISTS bot_statuses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        type TEXT DEFAULT 'playing',
        text TEXT
    )
    """)

    # --- [OPTIMIZACIÓN 1.A] ÍNDICES SQL ---
    # Esto hace que el /leaderboard sea instantáneo incluso con 10,000 usuarios
    await db.execute("CREATE INDEX IF NOT EXISTS idx_ranking ON guild_stats(guild_id, rebirths DESC, level DESC, xp DESC)")
    
    # Migraciones
    try:
        await db.execute("ALTER TABLE guild_stats ADD COLUMN rebirths INTEGER DEFAULT 0")
    except: pass
        
    await db.commit()

# --- LÓGICA DE CACHÉ Y XP ---

def calculate_xp_required(level):
    return int(100 * (level ** 1.2))

async def add_xp(guild_id: int, user_id: int, amount: int):
    """
    Añade XP en MEMORIA (Caché).
    Solo se escribe en la DB cuando 'flush_xp_cache' se ejecuta.
    """
    key = (guild_id, user_id)
    
    # 1. Cargar en caché si no existe
    if key not in _xp_cache:
        row = await fetch_one("SELECT xp, level, rebirths FROM guild_stats WHERE guild_id = ? AND user_id = ?", (guild_id, user_id))
        if row:
            _xp_cache[key] = {
                'xp': row['xp'], 
                'level': row['level'], 
                'rebirths': row['rebirths'], 
                'dirty': False # 'dirty' significa que tiene cambios sin guardar
            }
        else:
            _xp_cache[key] = {'xp': 0, 'level': 1, 'rebirths': 0, 'dirty': False}
    
    # 2. Modificar en memoria
    data = _xp_cache[key]
    data['xp'] += amount
    data['dirty'] = True 
    
    # 3. Calcular Nivel (Igual que antes pero en RAM)
    required = calculate_xp_required(data['level'])
    leveled_up = False
    
    while data['xp'] >= required:
        data['xp'] -= required
        data['level'] += 1
        leveled_up = True
        required = calculate_xp_required(data['level'])
    
    # Nota: No hacemos 'INSERT/UPDATE' aquí. Se hará en segundo plano.
    return data['level'], leveled_up

async def flush_xp_cache():
    """Guarda todos los usuarios con cambios ('dirty') en la base de datos."""
    if not _xp_cache: return
    
    updates = []
    clean_keys = []
    
    # Identificar qué guardar
    for key, data in _xp_cache.items():
        if data['dirty']:
            # (xp, level, rebirths, guild_id, user_id)
            updates.append((data['xp'], data['level'], data['rebirths'], key[0], key[1]))
            data['dirty'] = False # Marcamos como guardado
        else:
            # Si no ha cambiado y lleva tiempo (podríamos limpiar RAM aquí si quisiéramos)
            pass

    if updates:
        # Guardado masivo (Mucho más rápido que uno por uno)
        db = await get_db()
        await db.executemany("""
            INSERT INTO guild_stats (xp, level, rebirths, guild_id, user_id) 
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(guild_id, user_id) DO UPDATE SET 
            xp = excluded.xp, level = excluded.level, rebirths = excluded.rebirths
        """, updates)
        await db.commit()
       # print(f"💾 [Optimización] Se guardaron {len(updates)} perfiles de XP.")

async def do_rebirth(guild_id: int, user_id: int):
    # Primero forzamos guardar caché para asegurar que leemos datos reales
    await flush_xp_cache()
    
    row = await fetch_one("SELECT level, rebirths FROM guild_stats WHERE guild_id = ? AND user_id = ?", (guild_id, user_id))
    
    if not row: return False, "no_data"
    if row['level'] < 100: return False, row['level']
    
    new_reb = row['rebirths'] + 1
    
    # Actualizamos DB
    await execute("UPDATE guild_stats SET level = 1, xp = 0, rebirths = ? WHERE guild_id = ? AND user_id = ?", (new_reb, guild_id, user_id))
    
    # Actualizamos Caché si existe
    key = (guild_id, user_id)
    if key in _xp_cache:
        _xp_cache[key]['level'] = 1
        _xp_cache[key]['xp'] = 0
        _xp_cache[key]['rebirths'] = new_reb
        _xp_cache[key]['dirty'] = False
        
    return True, new_reb

# --- HELPERS ---
async def execute(query, params=()):
    db = await get_db()
    await db.execute(query, params)
    await db.commit()

async def fetch_one(query, params=()):
    db = await get_db()
    async with db.execute(query, params) as c: return await c.fetchone()

async def fetch_all(query, params=()):
    db = await get_db()
    async with db.execute(query, params) as c: return await c.fetchall()