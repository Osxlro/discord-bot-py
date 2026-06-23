import asyncio
import time
import random
import logging
import aiohttp
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

class TokenBucket:
    def __init__(self, capacity: int, fill_rate: float):
        """
        capacity: Capacidad máxima del balde de tokens.
        fill_rate: Cantidad de tokens añadidos por segundo.
        """
        self.capacity = capacity
        self.fill_rate = fill_rate
        self.tokens = capacity
        self.last_update = time.monotonic()
        self.lock = asyncio.Lock()

    async def consume(self, tokens: int = 1):
        async with self.lock:
            now = time.monotonic()
            elapsed = now - self.last_update
            self.last_update = now
            self.tokens = min(self.capacity, self.tokens + elapsed * self.fill_rate)
            
            if self.tokens < tokens:
                wait_time = (tokens - self.tokens) / self.fill_rate
                # Agregar jitter al tiempo de espera
                wait_time += random.uniform(0.01, 0.1)
                logger.debug(f"Rate limit alcanzado. Esperando {wait_time:.2f}s antes de proceder.")
                await asyncio.sleep(wait_time)
                self.tokens = 0
            else:
                self.tokens -= tokens

# Limitadores por dominio para no bloquear peticiones de otros servicios
_LIMITERS = {}
_SESSION = None

def get_limiter(domain: str) -> TokenBucket:
    if domain not in _LIMITERS:
        # Por defecto: Máximo 5 peticiones simultáneas, recupera 0.5 tokens por segundo (1 cada 2 segundos)
        _LIMITERS[domain] = TokenBucket(capacity=5, fill_rate=0.5)
    return _LIMITERS[domain]

async def get_session() -> aiohttp.ClientSession:
    global _SESSION
    if _SESSION is None or _SESSION.closed:
        _SESSION = aiohttp.ClientSession()
    return _SESSION

async def close_session():
    global _SESSION
    if _SESSION and not _SESSION.closed:
        await _SESSION.close()
        _SESSION = None

async def fetch_json(url: str, method: str = "GET", params: dict = None, json_data: dict = None, headers: dict = None, timeout: float = 10.0, max_retries: int = 3, base_delay: float = 2.0) -> dict | list | None:
    """
    Realiza una petición HTTP y retorna el contenido JSON.
    Aplica rate-limiting logic por dominio y exponencial backoff con jitter en caso de error.
    """
    domain = urlparse(url).netloc
    limiter = get_limiter(domain)
    
    # Consumir token antes del request
    await limiter.consume(1)
    
    session = await get_session()
    
    for attempt in range(1, max_retries + 1):
        try:
            async with session.request(
                method, 
                url, 
                params=params, 
                json=json_data, 
                headers=headers, 
                timeout=aiohttp.ClientTimeout(total=timeout)
            ) as resp:
                if resp.status == 200:
                    try:
                        return await resp.json()
                    except Exception as e:
                        logger.error(f"Error parseando JSON de {url}: {e}")
                        return None
                
                # Manejar códigos reintentables
                if resp.status in (429, 500, 502, 503, 504):
                    logger.warning(
                        f"⚠️ Error HTTP {resp.status} al acceder a {url} (Intento {attempt}/{max_retries})."
                    )
                else:
                    logger.error(
                        f"❌ Error HTTP {resp.status} al acceder a {url}. No se reintentará."
                    )
                    return None
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            logger.warning(
                f"⚠️ Error de red/timeout ({e}) al acceder a {url} (Intento {attempt}/{max_retries})."
            )
            
        # Calcular tiempo de espera para el backoff exponencial
        if attempt < max_retries:
            delay = base_delay * (2 ** (attempt - 1)) + random.uniform(0.1, 0.5)
            await asyncio.sleep(delay)
            
    logger.error(f"❌ Fallaron todos los {max_retries} intentos de petición HTTP a {url}.")
    return None
