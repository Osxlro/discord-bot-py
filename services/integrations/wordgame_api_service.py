import aiohttp
import logging

logger = logging.getLogger(__name__)

WORDGAME_API_BASE = "https://www.wordgamedb.com/api/v2"

async def fetch_words(category: str = None, min_letters: int = None, max_letters: int = None) -> list[dict]:
    """
    Obtiene palabras de wordgamedb.com API filtradas por categoría y cantidad de letras.
    
    Args:
        category (str): Opcional. Categoría de la palabra ('animal', 'country', 'food', 'plant', 'sport').
        min_letters (int): Opcional. Mínimo número de letras.
        max_letters (int): Opcional. Máximo número de letras.
        
    Returns:
        list[dict]: Lista de diccionarios de palabras, o lista vacía si falla.
    """
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
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    words = data.get("words", [])
                    return words
                else:
                    logger.warning(f"WordGameDB API respondió con código de estado HTTP {resp.status}")
    except Exception as e:
        logger.error(f"Error al conectar con WordGameDB API: {e}", exc_info=True)
        
    return []
