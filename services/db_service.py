import aiosqlite
import os
from config import settings

DATA_DIR = os.path.join(settings.BASE_DIR, "data")
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

DB_NAME = "database.sqlite3"
DB_PATH = os.path.join(DATA_DIR, DB_NAME)

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        # Tabla Usuarios (Configuración Personal)
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
        
        # Tabla Estadísticas por Servidor (XP y Nivel Local) - NUEVA
        await db.execute("""
        CREATE TABLE IF NOT EXISTS guild_stats (
            guild_id INTEGER,
            user_id INTEGER,
            xp INTEGER DEFAULT 0,
            level INTEGER DEFAULT 1,
            PRIMARY KEY (guild_id, user_id)
        )
        """)
        
        # Tabla Configuración de Servidor (Configuración Global)
        # Añadimos logs_channel_id
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
            server_birthday_msg TEXT DEFAULT NULL
        )
        """)

        # --- MIGRACIONES ---
        # Añadimos columnas nuevas de forma segura
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
            "ALTER TABLE guild_config ADD COLUMN language TEXT DEFAULT 'es'"
        ]
        
        for query in migraciones:
            try:
                await db.execute(query)
            except:
                pass
        
        await db.commit()
        print(f"💾 Base de datos conectada: {DB_PATH}")

# ... (Mantener las funciones execute, fetch_one, fetch_all igual que antes) ...
async def execute(query: str, params: tuple = ()):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(query, params)
        await db.commit()

async def fetch_one(query: str, params: tuple = ()):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(query, params)
        return await cursor.fetchone()

async def fetch_all(query: str, params: tuple = ()):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(query, params)
        return await cursor.fetchall()