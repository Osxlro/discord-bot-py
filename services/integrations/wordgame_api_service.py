import logging
import time
from services.utils import http_client

logger = logging.getLogger(__name__)

WORDGAME_API_BASE = "https://www.wordgamedb.com/api/v2"

# Caché total en memoria
_ALL_WORDS_CACHE = None
_ALL_WORDS_TIMESTAMP = 0
CACHE_TTL = 86400  # 24 horas

# Conjunto de palabras locales de respaldo ante fallos de red / API caída
LOCAL_FALLBACK_WORDS = [
    {"word": "cobra", "category": "animal", "hint": "Serpiente con capucha venenosa de Asia y África."},
    {"word": "tigre", "category": "animal", "hint": "Gran felino depredador con pelaje naranja y rayas negras."},
    {"word": "elefante", "category": "animal", "hint": "Mamífero terrestre gigante con colmillos de marfil y trompa."},
    {"word": "delfin", "category": "animal", "hint": "Mamífero acuático inteligente conocido por sus saltos y silbidos."},
    {"word": "aguila", "category": "animal", "hint": "Ave rapaz majestuosa con vista extremadamente aguda."},
    {"word": "tiburon", "category": "animal", "hint": "Depredador marino con varias filas de dientes afilados."},
    {"word": "platano", "category": "food", "hint": "Fruta tropical alargada de color amarillo y rica en potasio."},
    {"word": "pizza", "category": "food", "hint": "Plato italiano horneado con base de masa, tomate y queso fundido."},
    {"word": "manzana", "category": "food", "hint": "Fruta crujiente que puede ser roja, verde o amarilla."},
    {"word": "chocolate", "category": "food", "hint": "Dulce elaborado a partir de las semillas del cacao."},
    {"word": "hamburguesa", "category": "food", "hint": "Sándwich de carne picada cocinada a la parrilla."},
    {"word": "guitarra", "category": "instrument", "hint": "Instrumento musical de cuerda tocado con los dedos o púa."},
    {"word": "piano", "category": "instrument", "hint": "Instrumento musical grande con teclado de teclas blancas y negras."},
    {"word": "trompeta", "category": "instrument", "hint": "Instrumento de viento-metal de tamaño pequeño con tres pistones."},
    {"word": "flauta", "category": "instrument", "hint": "Instrumento de viento cilíndrico con agujeros que se tocan con los dedos."},
    {"word": "bateria", "category": "instrument", "hint": "Conjunto de instrumentos de percusión (tambores, platillos)."},
    {"word": "tokio", "category": "city", "hint": "Capital de Japón, una mezcla metropolitana de tradición y tecnología."},
    {"word": "paris", "category": "city", "hint": "Capital de Francia, famosa por la Torre Eiffel y el arte."},
    {"word": "roma", "category": "city", "hint": "Capital de Italia, conocida por el Coliseo y su historia antigua."},
    {"word": "madrid", "category": "city", "hint": "Capital de España, conocida por sus museos y plazas reales."},
    {"word": "londres", "category": "city", "hint": "Capital del Reino Unido, famosa por el Big Ben y el río Támesis."},
    {"word": "computadora", "category": "technology", "hint": "Dispositivo electrónico que procesa datos e instrucciones."},
    {"word": "telefono", "category": "technology", "hint": "Dispositivo móvil utilizado para comunicación y navegación."},
    {"word": "internet", "category": "technology", "hint": "Red informática mundial de comunicación descentralizada."},
    {"word": "satelite", "category": "technology", "hint": "Objeto artificial puesto en órbita alrededor de la Tierra."},
    {"word": "robot", "category": "technology", "hint": "Máquina programable automática capaz de realizar tareas físicas."},
    {"word": "futbol", "category": "sport", "hint": "Deporte de equipo jugado con un balón y dos porterías."},
    {"word": "tenis", "category": "sport", "hint": "Deporte jugado con raquetas y una pelota pequeña sobre una red."},
    {"word": "baloncesto", "category": "sport", "hint": "Deporte donde se encesta un balón en un aro elevado."},
    {"word": "natacion", "category": "sport", "hint": "Deporte o práctica de trasladarse en el agua usando extremidades."},
    {"word": "ciclismo", "category": "sport", "hint": "Deporte que consiste en el uso de la bicicleta."}
]

async def _get_all_words_cached() -> list[dict]:
    """Obtiene y cachea la lista completa de palabras del API externa."""
    global _ALL_WORDS_CACHE, _ALL_WORDS_TIMESTAMP
    now = time.time()
    
    if _ALL_WORDS_CACHE is not None and (now - _ALL_WORDS_TIMESTAMP < CACHE_TTL):
        logger.debug(f"💾 [WordGameDB] Recuperadas todas las palabras desde caché ({len(_ALL_WORDS_CACHE)} palabras)")
        return _ALL_WORDS_CACHE

    url = f"{WORDGAME_API_BASE}/words"
    params = {"limit": 1000}  # Descargar todo para evitar peticiones repetitivas
    
    try:
        logger.info("🌐 [WordGameDB] Descargando base completa de palabras desde el API externa...")
        data = await http_client.fetch_json(url, params=params, timeout=10)
        words = []
        if isinstance(data, dict):
            words = data.get("words", [])
        elif isinstance(data, list):
            words = data
            
        if words:
            _ALL_WORDS_CACHE = words
            _ALL_WORDS_TIMESTAMP = now
            return words
            
    except Exception as e:
        logger.error(f"Error descargando base completa de WordGameDB: {e}", exc_info=True)

    # Fallbacks estructurados
    if _ALL_WORDS_CACHE is not None:
        logger.warning("⚠️ [WordGameDB] Usando caché expirada de palabras como fallback ante fallo de red.")
        return _ALL_WORDS_CACHE

    logger.warning("⚠️ [WordGameDB] API caída y sin caché. Usando set de palabras locales de respaldo (LOCAL_FALLBACK_WORDS).")
    return LOCAL_FALLBACK_WORDS

async def fetch_words(category: str = None, min_letters: int = None, max_letters: int = None) -> list[dict]:
    """
    Obtiene palabras filtradas por categoría y cantidad de letras.
    Descarga todo una sola vez y filtra localmente en memoria para optimizar red.
    """
    all_words = await _get_all_words_cached()
    if not all_words:
        return []

    filtered = all_words

    # Filtro de categoría (case-insensitive)
    if category and category.lower() != "cualquiera":
        cat_lower = category.lower()
        filtered = [w for w in filtered if w.get("category", "").lower() == cat_lower]

    # Filtro de letras mínimas
    if min_letters is not None:
        filtered = [w for w in filtered if len(w.get("word", "")) >= min_letters]

    # Filtro de letras máximas
    if max_letters is not None:
        filtered = [w for w in filtered if len(w.get("word", "")) <= max_letters]

    return filtered
