import logging
import time
from services.utils import http_client

logger = logging.getLogger(__name__)

WORDGAME_API_BASE = "https://www.wordgamedb.com/api/v2"

# Estructura del caché: {cache_key: (timestamp, data)}
_WORDS_CACHE = {}
CACHE_TTL = 86400  # Guardar caché por 24 horas para evitar descargas redundantes

async def fetch_words(category: str = None, min_letters: int = None, max_letters: int = None) -> list[dict]:
    """
    Obtiene palabras de wordgamedb.com API filtradas por categoría y cantidad de letras,
    utilizando un caché en memoria de 24 horas para evitar descargas masivas repetitivas.
    """
    category_key = str(category).lower() if category else "none"
    min_key = str(min_letters) if min_letters is not None else "none"
    max_key = str(max_letters) if max_letters is not None else "none"
    cache_key = f"{category_key}:{min_key}:{max_key}"

    now = time.time()
    if cache_key in _WORDS_CACHE:
        timestamp, cached_data = _WORDS_CACHE[cache_key]
        if now - timestamp < CACHE_TTL:
            logger.debug(f"💾 [WordGameDB] Usando caché en memoria para: {cache_key} ({len(cached_data)} palabras)")
            return cached_data

    url = f"{WORDGAME_API_BASE}/words"
    params = {
        "limit": 1000  # Traer la mayor cantidad posible en una sola petición para aleatoriedad
    }
    
    if category and category.lower() != "cualquiera":
        params["category"] = category.lower()
        
    if min_letters is not None:
        params["minLetters"] = min_letters
        
    if max_letters is not None:
        params["maxLetters"] = max_letters
        
    try:
        logger.debug(f"🌐 [WordGameDB] Solicitando nuevas palabras desde la API: {params}")
        data = await http_client.fetch_json(url, params=params, timeout=10)
        words = []
        if isinstance(data, dict):
            words = data.get("words", [])
        elif isinstance(data, list):
            words = data
            
        if words:
            _WORDS_CACHE[cache_key] = (now, words)
            return words
    except Exception as e:
        logger.error(f"Error al conectar con WordGameDB API: {e}", exc_info=True)
        
    # Fallback: Si falla el API, pero tenemos datos expirados en el caché, los usamos
    if cache_key in _WORDS_CACHE:
        logger.warning(f"⚠️ [WordGameDB] Petición fallida. Usando caché expirada como fallback para {cache_key}.")
        return _WORDS_CACHE[cache_key][1]
        
    return []

