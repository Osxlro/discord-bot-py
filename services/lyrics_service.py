import aiohttp
import logging
import urllib.parse

logger = logging.getLogger(__name__)

async def get_lyrics(title: str, artist: str) -> str:
    """Busca letras en LRCLIB (Open Source)."""
    try:
        # Limpieza básica del título para mejorar la búsqueda
        # Elimina (Official Video), [4K], etc.
        title_clean = title.split("(")[0].split("[")[0].strip()
        
        params = {
            "artist_name": artist,
            "track_name": title_clean
        }
        
        url = "https://lrclib.net/api/get"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("plainLyrics") or data.get("syncedLyrics")
                elif resp.status == 404:
                    # Intento de búsqueda más amplia si falla la exacta
                    search_url = "https://lrclib.net/api/search"
                    params_search = {"q": f"{title_clean} {artist}"}
                    async with session.get(search_url, params=params_search) as resp_search:
                        if resp_search.status == 200:
                            data_search = await resp_search.json()
                            if data_search and isinstance(data_search, list) and len(data_search) > 0:
                                return data_search[0].get("plainLyrics")
    except Exception as e:
        logger.error(f"Error fetching lyrics: {e}")
    return None
