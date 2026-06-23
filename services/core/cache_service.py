import logging
import os
import json
from typing import Any, Optional

logger = logging.getLogger(__name__)

class CacheBackend:
    """Clase base abstracta para el backend de caché."""
    async def get(self, key: str) -> Optional[Any]:
        raise NotImplementedError()

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        raise NotImplementedError()

    async def delete(self, key: str) -> None:
        raise NotImplementedError()

    async def clear(self) -> None:
        raise NotImplementedError()

class MemoryCacheBackend(CacheBackend):
    """Implementación de caché en memoria RAM local."""
    def __init__(self) -> None:
        self._store = {}

    async def get(self, key: str) -> Optional[Any]:
        return self._store.get(key)

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        # En memoria local omitimos el TTL por simplicidad de desarrollo
        self._store[key] = value

    async def delete(self, key: str) -> None:
        if key in self._store:
            del self._store[key]

    async def clear(self) -> None:
        self._store.clear()

class RedisCacheBackend(CacheBackend):
    """Implementación de caché usando Redis (distribuido y escalable)."""
    def __init__(self, redis_url: str) -> None:
        self.redis_url = redis_url
        self._redis = None
        self._fallback = MemoryCacheBackend()
        self._active = False
        
        try:
            import redis.asyncio as aioredis
            self._aioredis = aioredis
        except ImportError:
            logger.warning("⚠️ La librería 'redis' no está instalada. Usando fallback de caché en memoria RAM.")
            self._aioredis = None

    async def _get_client(self) -> CacheBackend:
        if not self._aioredis:
            return self._fallback
            
        if self._redis is None:
            try:
                self._redis = self._aioredis.from_url(self.redis_url, decode_responses=True)
                self._active = True
                logger.info("⚡ Conexión exitosa con el servidor de caché Redis.")
            except Exception as e:
                logger.error(f"❌ Error al conectar a Redis: {e}. Usando fallback en memoria.")
                self._redis = self._fallback
                self._active = False
                
        return self._redis

    async def get(self, key: str) -> Optional[Any]:
        client = await self._get_client()
        if not self._active:
            return await client.get(key)
            
        try:
            val = await client.get(key)
            return json.loads(val) if val is not None else None
        except Exception:
            logger.exception(f"Error al leer de Redis (key: {key})")
            return await self._fallback.get(key)

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        client = await self._get_client()
        if not self._active:
            await client.set(key, value, ttl)
            return
            
        try:
            val_str = json.dumps(value)
            if ttl:
                await client.setex(key, ttl, val_str)
            else:
                await client.set(key, val_str)
        except Exception:
            logger.exception(f"Error al escribir en Redis (key: {key})")
            await self._fallback.set(key, value, ttl)

    async def delete(self, key: str) -> None:
        client = await self._get_client()
        if not self._active:
            await client.delete(key)
            return
            
        try:
            await client.delete(key)
        except Exception:
            logger.exception(f"Error al borrar de Redis (key: {key})")
            await self._fallback.delete(key)

    async def clear(self) -> None:
        client = await self._get_client()
        if not self._active:
            await client.clear()
            return
            
        try:
            await client.flushdb()
        except Exception:
            logger.exception("Error al limpiar base de datos en Redis")
            await self._fallback.clear()

# --- CONFIGURACIÓN E INSTANCIACIÓN ---
redis_uri = os.getenv("REDIS_URL")
if redis_uri:
    cache = RedisCacheBackend(redis_uri)
else:
    cache = MemoryCacheBackend()
