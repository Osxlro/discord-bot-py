import pickle
import logging
from typing import Any, Dict, Optional
from services.core import db_service

logger = logging.getLogger(__name__)

async def store(namespace: str, key: Any, data: Any) -> None:
    """
    Serializa y guarda cualquier objeto de Python en la base de datos SQLite en formato binario.

    Args:
        namespace: Espacio de nombres para organizar los datos.
        key: Clave única identificadora de los datos.
        data: Cualquier objeto serializable de Python.
    """
    try:
        binary_data = pickle.dumps(data)
        await db_service.execute(
            "INSERT INTO bot_persistence (namespace, key, data, created_at) VALUES (?, ?, ?, CURRENT_TIMESTAMP) "
            "ON CONFLICT(namespace, key) DO UPDATE SET data = excluded.data, created_at = CURRENT_TIMESTAMP",
            (namespace, str(key), binary_data)
        )
    except Exception:
        logger.exception(f"❌ Error guardando persistencia para {namespace}:{key}")

async def load(namespace: str, key: Any) -> Optional[Any]:
    """
    Carga y deserializa un objeto desde la tabla de persistencia binaria.

    Args:
        namespace: Espacio de nombres asociado al dato.
        key: Clave única del dato.

    Returns:
        El objeto de Python deserializado, o None si no se encuentra.
    """
    row = await db_service.fetch_one(
        "SELECT data FROM bot_persistence WHERE namespace = ? AND key = ?",
        (namespace, str(key))
    )
    if row:
        try:
            return pickle.loads(row['data'])
        except Exception:
            logger.exception(f"❌ Error al deserializar datos para {namespace}:{key}")
            return None
    return None

async def load_all(namespace: str) -> Dict[str, Any]:
    """
    Retorna todos los objetos almacenados bajo un mismo espacio de nombres.

    Args:
        namespace: Espacio de nombres a filtrar.

    Returns:
        Un diccionario mapeando clave a su objeto deserializado.
    """
    rows = await db_service.fetch_all(
        "SELECT key, data FROM bot_persistence WHERE namespace = ?",
        (namespace,)
    )
    result = {}
    for row in rows:
        try:
            result[row['key']] = pickle.loads(row['data'])
        except Exception:
            logger.exception(f"❌ Error al deserializar elemento en namespace {namespace}")
    return result

async def clear(namespace: str, key: Optional[Any] = None) -> None:
    """
    Elimina datos de persistencia. Si la clave es None, limpia el namespace completo.

    Args:
        namespace: Espacio de nombres.
        key: Clave opcional a eliminar.
    """
    if key:
        await db_service.execute("DELETE FROM bot_persistence WHERE namespace = ? AND key = ?", (namespace, str(key)))
    else:
        await db_service.execute("DELETE FROM bot_persistence WHERE namespace = ?", (namespace,))