import urllib.parse
import logging
from services.utils import http_client
from services.utils.cache_helper import SimpleTTLCache

logger = logging.getLogger(__name__)

# Caché con límite de 200 entradas y expiración de 12 horas (43200 segundos)
_translation_cache = SimpleTTLCache(max_size=200, ttl=43200)

async def traducir(texto: str, idioma_destino: str = 'es') -> dict:
    """
    Función asíncrona pública.
    Realiza la traducción de forma asíncrona usando la sesión global de http_client,
    evitando crear conexiones HTTP redundantes y previniendo bloqueos de hilo.
    """
    if not texto:
        return {
            "original": texto,
            "traducido": texto,
            "idioma": idioma_destino
        }

    key = (texto.strip(), idioma_destino)
    cached = _translation_cache.get(key)
    if cached is not None:
        logger.debug(f"💾 [Translator] Usando caché para traducción: '{texto[:30]}...' -> {idioma_destino}")
        return {
            "original": texto,
            "traducido": cached,
            "idioma": idioma_destino
        }

    texto_encoded = urllib.parse.quote(texto)
    url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl={idioma_destino}&dt=t&q={texto_encoded}"

    try:
        data = await http_client.fetch_json(url, timeout=10)
        if data and isinstance(data, list) and len(data) > 0 and isinstance(data[0], list):
            # Google Translate API agrupa las líneas del texto traducido en el primer elemento de la lista
            traducciones = []
            for part in data[0]:
                if part and isinstance(part, list) and len(part) > 0:
                    traducciones.append(part[0])
            
            resultado = "".join(traducciones)
            if resultado:
                _translation_cache.set(key, resultado)
                return {
                    "original": texto,
                    "traducido": resultado,
                    "idioma": idioma_destino
                }
                
        raise ValueError("Respuesta de API de traducción vacía o inválida.")
    except Exception as e:
        logger.error(f"Error al conectar con el servicio de traducción: {e}")
        raise ValueError(f"Error al conectar con el servicio de traducción: {e}")