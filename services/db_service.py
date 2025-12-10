import aiosqlite
import os
from config import settings

DB_NAME = "database.sqlite3"
DB_PATH = os.path.join(settings.BASE_DIR, DB_NAME)

async def init_db():
    """Inicializa la base de datos y actualiza la estructura si es necesario."""
    async with aiosqlite.connect(DB_PATH) as db:
        # 1. Crear tabla si no existe (Estructura Base)
        await db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            xp INTEGER DEFAULT 0,
            level INTEGER DEFAULT 1,
            birthday TEXT DEFAULT NULL,
            celebrate BOOLEAN DEFAULT 1
        )
        """)
        
        await db.execute("""
        CREATE TABLE IF NOT EXISTS guild_config (
            guild_id INTEGER PRIMARY KEY,
            chaos_enabled BOOLEAN DEFAULT 1,
            welcome_channel_id INTEGER DEFAULT 0
        )
        """)

        # 2. Migración Automática: Intentar agregar columna 'celebrate' si la tabla es antigua
        # Esto es necesario porque tu DB ya existe y no tiene esa columna.
        try:
            await db.execute("ALTER TABLE users ADD COLUMN celebrate BOOLEAN DEFAULT 1")
            print("🔧 Base de datos actualizada: Columna 'celebrate' agregada.")
        except Exception:
            # Si falla es porque la columna ya existe, así que ignoramos el error.
            pass
        
        await db.commit()
        print(f"💾 Base de datos conectada y verificada: {DB_NAME}")

# ... (Las funciones execute, fetch_one, fetch_all se quedan IGUAL) ...
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