import aiosqlite
import os
from config import settings

# --- CAMBIO: Definir carpeta de datos ---
DATA_DIR = os.path.join(settings.BASE_DIR, "data")
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

DB_NAME = "database.sqlite3"
DB_PATH = os.path.join(DATA_DIR, DB_NAME) # Ahora se guarda en data/

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        # ... (Tu código de creación de tablas users y guild_config sigue IGUAL) ...
        await db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            xp INTEGER DEFAULT 0,
            level INTEGER DEFAULT 1,
            birthday TEXT DEFAULT NULL,
            celebrate BOOLEAN DEFAULT 1,
            custom_prefix TEXT DEFAULT NULL 
        )
        """) # <--- AGREGAMOS custom_prefix AQUÍ ARRIBA ^
        
        await db.execute("""
        CREATE TABLE IF NOT EXISTS guild_config (
            guild_id INTEGER PRIMARY KEY,
            chaos_enabled BOOLEAN DEFAULT 1,
            welcome_channel_id INTEGER DEFAULT 0,
            confessions_channel_id INTEGER DEFAULT 0
        )
        """)

        # --- MIGRACIONES ---
        # Agregamos la migración para el prefix si la tabla ya existía
        try:
            await db.execute("ALTER TABLE users ADD COLUMN custom_prefix TEXT DEFAULT NULL")
            print("🔧 Base de datos: Columna 'custom_prefix' agregada.")
        except Exception:
            pass
        
        # ... (Resto de migraciones celebracion, confesiones, etc) ...
        
        await db.commit()
        print(f"💾 Base de datos cargada desde: {DB_PATH}")

# ... (El resto de funciones execute, fetch_one, etc. IGUAL) ...
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