import logging
import re
from services.utils import http_client
from services.utils.cache_helper import SimpleTTLCache

logger = logging.getLogger(__name__)

# Caché con límite de 100 letras de canciones y expiración de 24 horas (86400 segundos)
_lyrics_cache = SimpleTTLCache(max_size=100, ttl=86400)

async def get_lyrics(title: str, artist: str) -> str:
    """Busca letras en LRCLIB (Open Source)."""
    if not title:
        return None
        
    artist_name = artist or ""
    key = (title.lower().strip(), artist_name.lower().strip())
    
    cached = _lyrics_cache.get(key)
    if cached is not None:
        logger.debug(f"💾 [Lyrics] Usando caché para letra de: {title} - {artist_name}")
        return cached

    try:
        # Limpieza avanzada del título para maximizar aciertos
        title_clean = re.sub(r"[\(\[].*?[\)\]]", "", title)
        noise = ["official video", "official audio", "lyrics", "hd", "4k", "video oficial", "letra", "audio"]
        for n in noise:
            title_clean = re.compile(re.escape(n), re.IGNORECASE).sub("", title_clean)
        title_clean = title_clean.strip()
        
        params = {"artist_name": artist_name, "track_name": title_clean}
        url = "https://lrclib.net/api/get"
        
        data = await http_client.fetch_json(url, params=params, timeout=10)
        if data and isinstance(data, dict):
            lyrics = data.get("plainLyrics") or data.get("syncedLyrics")
            if lyrics:
                _lyrics_cache.set(key, lyrics)
                return lyrics
            
        # Intento de búsqueda más amplia si falla o no existe (404)
        search_url = "https://lrclib.net/api/search"
        params_search = {"q": f"{title_clean} {artist_name}"}
        data_search = await http_client.fetch_json(search_url, params=params_search, timeout=10)
        if data_search and isinstance(data_search, list) and len(data_search) > 0:
            lyrics = data_search[0].get("plainLyrics")
            if lyrics:
                _lyrics_cache.set(key, lyrics)
                return lyrics
    except Exception as e:
        logger.error(f"Error fetching lyrics: {e}")
    return None
