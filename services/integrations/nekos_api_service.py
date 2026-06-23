import logging
from services.utils import http_client

logger = logging.getLogger(__name__)

NEKOS_API_BASE = "https://api.nekosapi.com/v4"

async def get_random_image(rating: str = "safe", tag: str = None) -> dict | None:
    """
    Obtiene una imagen/gif aleatoria de NekosAPI v4.
    
    Args:
        rating (str): Filtrado de contenido ('safe', 'suggestive', 'borderline', 'explicit').
                     Por defecto es 'safe' para evitar contenido inapropiado.
        tag (str): Opcional. Filtra por etiqueta específica.
        
    Returns:
        dict: Los metadatos de la imagen o None si falla.
    """
    url = f"{NEKOS_API_BASE}/images/random"
    params = {
        "rating": rating,
        "limit": 1
    }
    if tag:
        params["tags"] = tag

    try:
        data = await http_client.fetch_json(url, params=params, timeout=10)
        if data and isinstance(data, list) and len(data) > 0:
            return data[0]
        logger.warning("NekosAPI devolvió una respuesta vacía o con formato inesperado.")
    except Exception as e:
        logger.error(f"Error al conectar con NekosAPI: {e}", exc_info=True)
    return None

