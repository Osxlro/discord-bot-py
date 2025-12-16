import aiosqlite
import os
import logging
from config import settings

# Configuración de rutas
DATA_DIR = os.path.join(settings.BASE_DIR, "data")
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

DB_NAME = "database.sqlite3"
DB_PATH = os.path.join(DATA_DIR, DB_NAME)

# --- VARIABLE GLOBAL PARA LA CONEXIÓN (SINGLETON) ---
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
        print(f"🔌 Base de datos conectada (Singleton): {DB_PATH}")
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
    
    # 5. Tabla de Estados del Bot (NUEVA)
    await db.execute("""
    CREATE TABLE IF NOT EXISTS bot_statuses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        type TEXT DEFAULT 'playing',
        text TEXT
    )
    """)
    
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

# --- FUNCIONES DE CONSULTA OPTIMIZADAS ---

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