import pickle
import logging
from services import db_service

logger = logging.getLogger(__name__)

async def store(namespace: str, key: str, data: any):
    """Serializa y guarda cualquier objeto de Python en formato binario."""
    try:
        binary_data = pickle.dumps(data)
        await db_service.execute(
            "INSERT INTO bot_persistence (namespace, key, data) VALUES (?, ?, ?) "
            "ON CONFLICT(namespace, key) DO UPDATE SET data = excluded.data",
            (namespace, str(key), binary_data)
        )
    except Exception:
        logger.exception(f"❌ Error guardando persistencia para {namespace}:{key}")

async def load(namespace: str, key: str) -> any:
    """Carga y deserializa un objeto desde la base de datos."""
    row = await db_service.fetch_one(
        "SELECT data FROM bot_persistence WHERE namespace = ? AND key = ?",
        (namespace, str(key))
    )
    if row:
        return pickle.loads(row['data'])
    return None

async def load_all(namespace: str) -> dict:
    """Retorna todos los objetos bajo un mismo namespace."""
    rows = await db_service.fetch_all(
        "SELECT key, data FROM bot_persistence WHERE namespace = ?",
        (namespace,)
    )
    return {row['key']: pickle.loads(row['data']) for row in rows}

async def clear(namespace: str, key: str = None):
    """Elimina datos de persistencia. Si key es None, limpia el namespace completo."""
    if key:
        await db_service.execute("DELETE FROM bot_persistence WHERE namespace = ? AND key = ?", (namespace, str(key)))
    else:
        await db_service.execute("DELETE FROM bot_persistence WHERE namespace = ?", (namespace,))