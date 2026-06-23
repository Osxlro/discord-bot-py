import logging
import re
from services.utils import http_client

logger = logging.getLogger(__name__)

async def get_lyrics(title: str, artist: str) -> str:
    """Busca letras en LRCLIB (Open Source)."""
    try:
        # Limpieza avanzada del título para maximizar aciertos
        title_clean = re.sub(r"[\(\[].*?[\)\]]", "", title)
        noise = ["official video", "official audio", "lyrics", "hd", "4k", "video oficial", "letra", "audio"]
        for n in noise:
            title_clean = re.compile(re.escape(n), re.IGNORECASE).sub("", title_clean)
        title_clean = title_clean.strip()
        
        params = {"artist_name": artist, "track_name": title_clean}
        url = "https://lrclib.net/api/get"
        
        data = await http_client.fetch_json(url, params=params, timeout=10)
        if data and isinstance(data, dict):
            return data.get("plainLyrics") or data.get("syncedLyrics")
            
        # Intento de búsqueda más amplia si falla o no existe (404)
        search_url = "https://lrclib.net/api/search"
        params_search = {"q": f"{title_clean} {artist}"}
        data_search = await http_client.fetch_json(search_url, params=params_search, timeout=10)
        if data_search and isinstance(data_search, list) and len(data_search) > 0:
            return data_search[0].get("plainLyrics")
    except Exception as e:
        logger.error(f"Error fetching lyrics: {e}")
    return None

