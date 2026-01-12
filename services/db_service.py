import aiosqlite
import os
from config import settings

# Configuración de rutas
DATA_DIR = os.path.join(settings.BASE_DIR, "data")
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

DB_NAME = "database.sqlite3"
DB_PATH = os.path.join(DATA_DIR, DB_NAME)

_connection = None

async def get_db() -> aiosqlite.Connection:
    """
    Retorna la conexión activa a la base de datos.
    Si no existe, la crea.
    """
    global _connection
    if _connection is None:
        # Creamos la conexión y la guardamos en la variable global
        _connection = await aiosqlite.connect(DB_PATH)
        # Esto permite acceder a columnas por nombre (row['id'])
        _connection.row_factory = aiosqlite.Row
        print(f"🔌 Base de datos conectada: {DB_PATH}")
    return _connection

async def close_db():
    """Cierra la conexión de forma segura (para cuando el bot se apaga)."""
    global _connection
    if _connection:
        await _connection.close()
        _connection = None
        print("🔌 Base de datos desconectada.")

async def init_db():
    """Inicializa las tablas y aplica migraciones usando la conexión única."""
    db = await get_db()
    
    # 1. Tabla Usuarios
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
    
    # 2. Tabla Estadísticas por Servidor
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
    
    # 3. Tabla Configuración de Servidor
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
        language TEXT DEFAULT 'es'
    )
    """)

    # 4. Migraciones (Columnas nuevas)
    migraciones = [
        "ALTER TABLE guild_config ADD COLUMN birthday_channel_id INTEGER DEFAULT 0",
        "ALTER TABLE users ADD COLUMN custom_prefix TEXT DEFAULT NULL",
        "ALTER TABLE guild_config ADD COLUMN mention_response TEXT DEFAULT NULL",
        "ALTER TABLE guild_config ADD COLUMN confessions_channel_id INTEGER DEFAULT 0",
        "ALTER TABLE guild_config ADD COLUMN autorole_id INTEGER DEFAULT 0",
        "ALTER TABLE guild_config ADD COLUMN logs_channel_id INTEGER DEFAULT 0",
        "ALTER TABLE users ADD COLUMN description TEXT DEFAULT 'Sin descripción.'",
        "ALTER TABLE users ADD COLUMN personal_level_msg TEXT DEFAULT NULL",
        "ALTER TABLE users ADD COLUMN personal_birthday_msg TEXT DEFAULT NULL",
        "ALTER TABLE guild_config ADD COLUMN server_level_msg TEXT DEFAULT NULL",
        "ALTER TABLE guild_config ADD COLUMN server_birthday_msg TEXT DEFAULT NULL",
        "ALTER TABLE guild_config ADD COLUMN chaos_probability REAL DEFAULT 0.01",
        "ALTER TABLE guild_config ADD COLUMN language TEXT DEFAULT 'es'",
        "ALTER TABLE guild_config ADD COLUMN server_kick_msg TEXT DEFAULT NULL",
        "ALTER TABLE guild_config ADD COLUMN server_ban_msg TEXT DEFAULT NULL"
    ]
    
    for query in migraciones:
        try:
            await db.execute(query)
        except Exception:
            # Ignoramos error si la columna ya existe
            pass
    
    # 5. Tabla de Estados del Bot
    await db.execute("""
    CREATE TABLE IF NOT EXISTS bot_statuses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        type TEXT DEFAULT 'playing',
        text TEXT
    )
    """)
    
    await db.execute("""
    CREATE TABLE IF NOT EXISTS chat_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        guild_id INTEGER,
        user_name TEXT,
        content TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    await db.execute("CREATE INDEX IF NOT EXISTS idx_chat_guild ON chat_logs(guild_id)")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_chat_content ON chat_logs(content)")
    
    # Insertar estados por defecto si la tabla está vacía
    row = await fetch_one("SELECT count(*) as count FROM bot_statuses")
    if row['count'] == 0:
        defaults = [
            ("playing", "Visual Studio Code"),
            ("watching", "a los usuarios"),
            ("listening", "/help")
        ]
        await db.executemany("INSERT INTO bot_statuses (type, text) VALUES (?, ?)", defaults)
        await db.commit()
    
    await db.commit()

# --- FUNCIONES DE XP Y NIVEL ---

def calculate_xp_required(level):
    """Fórmula exponencial: XP requerida para el SIGUIENTE nivel."""
    # Ejemplo: Nivel 1->2 = 100xp. Nivel 10->11 = ~1500xp
    return int(100 * (level ** 1.2)) 

async def add_xp(guild_id: int, user_id: int, amount: int):
    """
    Añade XP y maneja subidas de nivel con REINICIO de XP.
    Retorna (nuevo_nivel, subio_de_nivel_bool)
    """
    db = await get_db()
    
    # 1. Obtener estado actual
    row = await fetch_one(
        "SELECT xp, level, rebirths FROM guild_stats WHERE guild_id = ? AND user_id = ?", 
        (guild_id, user_id)
    )
    
    current_xp = 0
    current_level = 1
    current_rebirths = 0
    
    if row:
        current_xp = row['xp']
        current_level = row['level']
        current_rebirths = row['rebirths']
    
    # 2. Añadir XP
    current_xp += amount
    xp_needed = calculate_xp_required(current_level)
    
    leveled_up = False
    
    # 3. Comprobar Level Up (Bucle por si sube varios niveles de golpe)
    while current_xp >= xp_needed:
        current_xp -= xp_needed # Restamos la XP usada (Aquí está el fix)
        current_level += 1
        leveled_up = True
        xp_needed = calculate_xp_required(current_level) # Recalcular para el siguiente
    
    # 4. Guardar cambios
    await db.execute("""
    INSERT INTO guild_stats (guild_id, user_id, xp, level, rebirths)
    VALUES (?, ?, ?, ?, ?)
    ON CONFLICT(guild_id, user_id) DO UPDATE SET
        xp = excluded.xp,
        level = excluded.level
    """, (guild_id, user_id, current_xp, current_level, current_rebirths))
    
    await db.commit()
    return current_level, leveled_up

async def do_rebirth(guild_id: int, user_id: int):
    """Intenta hacer un rebirth. Retorna (success, mensaje_error_o_nuevo_count)"""
    row = await fetch_one(
        "SELECT level, rebirths FROM guild_stats WHERE guild_id = ? AND user_id = ?", 
        (guild_id, user_id)
    )
    
    if not row:
        return False, "No tienes datos en este servidor."
        
    if row['level'] < 100:
        return False, row['level'] # Retornamos nivel actual para el mensaje de error
        
    new_rebirths = row['rebirths'] + 1
    
    # Resetear Stats
    await execute("""
        UPDATE guild_stats 
        SET level = 1, xp = 0, rebirths = ? 
        WHERE guild_id = ? AND user_id = ?
    """, (new_rebirths, guild_id, user_id))
    
    return True, new_rebirths

# --- FUNCIONES DE CONSULTA ---

async def execute(query: str, params: tuple = ()):
    """Ejecuta una instrucción (INSERT, UPDATE, DELETE) sin cerrar la conexión."""
    db = await get_db()
    await db.execute(query, params)
    await db.commit()

async def fetch_one(query: str, params: tuple = ()):
    """Obtiene una sola fila."""
    db = await get_db()
    async with db.execute(query, params) as cursor:
        return await cursor.fetchone()

async def fetch_all(query: str, params: tuple = ()):
    """Obtiene todas las filas."""
    db = await get_db()
    async with db.execute(query, params) as cursor:
        return await cursor.fetchall()