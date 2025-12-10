import aiosqlite
import os
from config import settings

DB_NAME = "database.sqlite3"
DB_PATH = os.path.join(settings.BASE_DIR, DB_NAME)

async def init_db():
    """Inicializa la base de datos y crea las tablas necesarias."""
    async with aiosqlite.connect(DB_PATH) as db:
        # Tabla de Usuarios (Ejemplo: Para cumpleaños, XP, Dinero)
        await db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            xp INTEGER DEFAULT 0,
            level INTEGER DEFAULT 1,
            birthday TEXT DEFAULT NULL
        )
        """)
        
        # Tabla de Configuración (Ej: Para el sistema de Chaos/Ruleta)
        await db.execute("""
        CREATE TABLE IF NOT EXISTS guild_config (
            guild_id INTEGER PRIMARY KEY,
            chaos_enabled BOOLEAN DEFAULT 1,
            welcome_channel_id INTEGER DEFAULT 0
        )
        """)
        
        await db.commit()
        print(f"💾 Base de datos conectada: {DB_NAME}")

async def execute(query: str, params: tuple = ()):
    """Ejecuta una instrucción (INSERT, UPDATE, DELETE)."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(query, params)
        await db.commit()

async def fetch_one(query: str, params: tuple = ()):
    """Busca un solo resultado (SELECT)."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row # Permite acceder a columnas por nombre
        cursor = await db.execute(query, params)
        return await cursor.fetchone()

async def fetch_all(query: str, params: tuple = ()):
    """Busca todos los resultados (SELECT)."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(query, params)
        return await cursor.fetchall()