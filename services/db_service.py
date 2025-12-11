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
            custom_prefix TEXT DEFAULT NULL 
        )
        """)
        
        # Tabla Configuración de Servidor (Configuración Global)
        # Añadimos logs_channel_id
        await db.execute("""
        CREATE TABLE IF NOT EXISTS guild_config (
            guild_id INTEGER PRIMARY KEY,
            chaos_enabled BOOLEAN DEFAULT 1,
            welcome_channel_id INTEGER DEFAULT 0,
            confessions_channel_id INTEGER DEFAULT 0,
            logs_channel_id INTEGER DEFAULT 0, 
            mention_response TEXT DEFAULT NULL
        )
        """)

        # --- MIGRACIONES ---
        # Ejecutamos migraciones previas para evitar errores
        try: await db.execute("ALTER TABLE users ADD COLUMN custom_prefix TEXT DEFAULT NULL")
        except: pass
        try: await db.execute("ALTER TABLE guild_config ADD COLUMN mention_response TEXT DEFAULT NULL")
        except: pass
        try: await db.execute("ALTER TABLE guild_config ADD COLUMN confessions_channel_id INTEGER DEFAULT 0")
        except: pass

        # NUEVA MIGRACIÓN: Logs
        try:
            await db.execute("ALTER TABLE guild_config ADD COLUMN logs_channel_id INTEGER DEFAULT 0")
            print("🔧 Base de datos: Columna 'logs_channel_id' agregada.")
        except Exception:
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