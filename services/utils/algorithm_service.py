import random
import asyncio
import aiohttp
import base64
import time
import wavelink
import logging
import datetime
from difflib import SequenceMatcher
from config import settings
from services.features import music_service

logger = logging.getLogger(__name__)

class RecommendationEngine:
    """
    Motor de recomendaciones avanzado (V2).
    Analiza patrones de escucha, estilos musicales y metadatos para generar
    una cola infinita que se siente natural y contextual.
    """
    
    def __init__(self):
        self.history_limit = settings.ALGORITHM_CONFIG["HISTORY_LIMIT"]
        self.similarity_threshold = settings.ALGORITHM_CONFIG["SIMILARITY_THRESHOLD"]
        self.style_keywords = settings.ALGORITHM_CONFIG["STYLE_KEYWORDS"]
        self.MOODS = settings.ALGORITHM_CONFIG["MOODS"]
        self.GENRE_MAP = settings.ALGORITHM_CONFIG["GENRE_MAP"]
        
        # Lista plana de artistas conocidos para scoring rápido
        self.KNOWN_ARTISTS = {artist.lower() for artists in self.GENRE_MAP.values() for artist in artists}
        
        # Configuración Spotify (Opcional)
        self.sp_client_id = settings.LAVALINK_CONFIG["SPOTIFY"]["CLIENT_ID"]
        self.sp_client_secret = settings.LAVALINK_CONFIG["SPOTIFY"]["CLIENT_SECRET"]
        self.sp_token = None
        self.sp_token_expiry = 0
        self._token_lock = asyncio.Lock()
        self._session = None
        self._skip_tracker = {} # guild_id: {genre: count}

    async def _get_session(self) -> aiohttp.ClientSession:
        """Obtiene o crea una sesión persistente para peticiones HTTP."""
        if self._session is None or self._session.closed:
            # TCPConnector optimiza el reuso de conexiones y evita fugas de sockets
            connector = aiohttp.TCPConnector(limit=10, ttl_dns_cache=300)
            self._session = aiohttp.ClientSession(connector=connector)
        return self._session

    async def close(self):
        """Cierra la sesión de aiohttp de forma segura."""
        if self._session and not self._session.closed:
            await self._session.close()

    async def _request(self, method: str, url: str, **kwargs) -> dict | None:
        """Realiza una petición HTTP genérica con manejo de errores y reintentos."""
        session = await self._get_session()
        try:
            timeout = aiohttp.ClientTimeout(total=10)
            async with session.request(method, url, timeout=timeout, **kwargs) as resp:
                if resp.status == 200:
                    # Validar que la respuesta sea JSON antes de parsear
                    if "application/json" in resp.headers.get("Content-Type", ""):
                        return await resp.json()
                    logger.error(f"⚠️ [Spotify API] Respuesta no es JSON en {url}")
                    return None
                elif resp.status == 429:
                    retry_after = int(resp.headers.get("Retry-After", 5))
                    logger.warning(f"⏳ [Spotify API] Rate limit. Reintentando en {retry_after}s")
                    await asyncio.sleep(retry_after)
                    return await self._request(method, url, **kwargs)
                else:
                    logger.error(f"❌ [Spotify API] Error {resp.status} en {url}")
        except Exception as e:
            logger.error(f"⚠️ Error en petición a {url}: {e}")
        return None

    async def _get_spotify_token(self):
        """Obtiene un token de acceso para la API de Spotify."""
        if not self.sp_client_id or not self.sp_client_secret: return None
        
        async with self._token_lock:
            if self.sp_token and time.time() < self.sp_token_expiry:
                return self.sp_token

        try:
            auth = base64.b64encode(f"{self.sp_client_id}:{self.sp_client_secret}".encode()).decode()
            data = await self._request(
                "POST",
                "https://accounts.spotify.com/api/token",
                headers={"Authorization": f"Basic {auth}"},
                data={"grant_type": "client_credentials"}
            )
            if data:
                self.sp_token = data["access_token"]
                self.sp_token_expiry = time.time() + data["expires_in"] - 60
                return self.sp_token
        except Exception:
            logger.exception("⚠️ Error obteniendo token Spotify")
        return None

    async def _get_spotify_context(self, seed_track: wavelink.Playable) -> dict:
        """Obtiene recomendaciones y características de audio de Spotify."""
        token = await self._get_spotify_token()
        if not token: return {}

        clean_title = music_service.clean_track_title(seed_track.title)
        query = f"{clean_title} {seed_track.author}"
        
        search_data = await self._request(
            "GET",
            "https://api.spotify.com/v1/search",
            headers={"Authorization": f"Bearer {token}"},
            params={"q": query, "type": "track", "limit": 1}
        )
        if not search_data or not search_data["tracks"]["items"]: return {}
        spotify_id = search_data["tracks"]["items"][0]["id"]

        features = await self._request(
            "GET",
            f"https://api.spotify.com/v1/audio-features/{spotify_id}",
            headers={"Authorization": f"Bearer {token}"}
        ) or {}

        mood = self._get_current_mood()
        params = {
            "seed_tracks": spotify_id,
            "limit": 8,
            "target_energy": features.get("energy", self.MOODS[mood]["energy_range"][1]),
            "target_valence": features.get("valence", 0.5)
        }

        rec_data = await self._request(
            "GET",
            "https://api.spotify.com/v1/recommendations",
            headers={"Authorization": f"Bearer {token}"},
            params=params
        )
        if not rec_data: return {"features": features, "recs": []}
        
        recs = [f"{t['name']} - {t['artists'][0]['name']}" for t in rec_data["tracks"]]
        return {"features": features, "recs": recs}

    def _get_current_mood(self) -> str:
        """Determina el mood basado en la hora local."""
        hour = datetime.datetime.now().hour
        if 0 <= hour < 6: return "late_night"
        if 6 <= hour < 12: return "morning"
        if 12 <= hour < 19: return "day"
        return "evening"

    def _is_similar(self, a: str, b: str) -> bool:
        """Compara dos títulos y devuelve True si son casi idénticos."""
        if a.lower() == b.lower(): return True
        return SequenceMatcher(None, a.lower(), b.lower()).ratio() > self.similarity_threshold

    def _get_artist_genre(self, artist: str) -> str:
        """Intenta determinar el género basado en el artista."""
        artist_low = artist.lower()
        for genre, artists in self.GENRE_MAP.items():
            if any(a.lower() in artist_low for a in artists):
                return genre
        return "unknown"

    def _get_related_known_artists(self, artist: str) -> list[str]:
        """Obtiene una lista de artistas conocidos del mismo género."""
        genre = self._get_artist_genre(artist)
        if genre != "unknown":
            # Retornamos artistas del mismo género excluyendo al actual
            return [a for a in self.GENRE_MAP[genre] if a.lower() not in artist.lower()]
        return []

    def _get_style_tags(self, title: str) -> set[str]:
        """Extrae etiquetas de estilo del título."""
        if not title: return set()
        return {tag for tag in self.style_keywords if tag in title.lower()}

    def _calculate_score(self, candidate: wavelink.Playable, seed: wavelink.Playable, seed_styles: set[str], mood: str, spotify_context: dict = None) -> int:
        """Asigna una puntuación de relevancia al candidato (0-100+)."""
        score = 100
        score += self._score_vibe(candidate, seed_styles, mood)
        score += self._score_metadata(candidate, seed)
        score += self._score_session_skips(candidate)
        return max(0, score)

    def _score_vibe(self, candidate: wavelink.Playable, seed_styles: set[str], mood: str) -> int:
        """Calcula bonificaciones basadas en el estilo y el mood actual."""
        bonus = 0
        cand_styles = self._get_style_tags(candidate.title)
        if seed_styles and not cand_styles:
            bonus -= 40
        common_styles = seed_styles & cand_styles
        bonus += len(common_styles) * 15

        cand_author = candidate.author.lower()
        if any(known in cand_author for known in self.KNOWN_ARTISTS):
            bonus += 60

        cand_genre = self._get_artist_genre(candidate.author)
        if cand_genre in self.MOODS[mood]["genres"]:
            bonus += 25
        return bonus

    def _score_session_skips(self, candidate: wavelink.Playable) -> int:
        """Penaliza géneros que han sido saltados frecuentemente en la sesión actual."""
        # Esta lógica requiere el guild_id, que pasaremos en el contexto futuro
        # Por ahora usamos una penalización base si el artista es muy similar al último saltado
        return 0 

    def _score_metadata(self, candidate: wavelink.Playable, seed: wavelink.Playable) -> int:
        """Analiza metadatos técnicos como duración e idioma."""
        adjustment = 0
        diff_ms = abs(candidate.length - seed.length)

        # Bonus por cohesión de autor (mismo artista)
        if candidate.author.lower() == seed.author.lower():
            adjustment += 40

        if diff_ms > 600000: adjustment -= 30
        elif diff_ms < 60000: adjustment += 10

        if "official video" in candidate.title.lower() and "official video" in seed.title.lower():
            adjustment -= 5
        if "live" in candidate.title.lower() and "live" not in seed.title.lower():
            adjustment -= 25

        if "cover" in seed.title.lower() and "cover" in candidate.title.lower() and candidate.author.lower() == seed.author.lower():
            adjustment -= 80

        is_spanish_seed = any(w in seed.title.lower() for w in [" de ", " la ", " el ", " con "])
        is_spanish_cand = any(w in candidate.title.lower() for w in [" de ", " la ", " el ", " con "])
        if is_spanish_seed != is_spanish_cand: adjustment -= 20
        return adjustment

    async def get_recommendation(self, player: wavelink.Player) -> wavelink.Playable:
        if not player.queue.history: return None

        # 1. Preparar Contexto
        history = list(player.queue.history)
        recent = history[-self.history_limit:]
        played_ids = {t.identifier for t in recent}
        played_titles = [t.title for t in recent]
        played_authors = {t.author.lower() for t in recent}

        seed = history[-1]
        author = seed.author or settings.ALGORITHM_CONFIG["DEFAULT_METADATA"]
        title = seed.title or settings.ALGORITHM_CONFIG["DEFAULT_METADATA"]
        seed_styles = self._get_style_tags(title)
        mood = self._get_current_mood()
        
        # --- ESTRATEGIA 1: SPOTIFY ---
        spotify_data = await self._get_spotify_context(seed)
        if spotify_data.get("recs"):
            rec = await self._resolve_spotify_recs(spotify_data, seed, seed_styles, mood, played_ids)
            if rec: return rec

        # --- ESTRATEGIA 2: HEURÍSTICA ---
        artist_streak = self._get_artist_streak(history, author)
        provider = settings.LAVALINK_CONFIG.get("SEARCH_PROVIDER", "ytsearch")
        queries = self._get_heuristic_queries(provider, author, title, seed_styles, artist_streak)
        
        candidates = await self._fetch_candidates(queries)

        scored = []
        for track in candidates:
            if self._is_valid_candidate(track, played_ids, played_titles, played_authors, artist_streak, author):
                score = self._calculate_score(track, seed, seed_styles, mood, spotify_data)
                scored.append((track, score))

        if scored:
            return self._select_best_candidate(scored)
            
        return await self._get_fallback_recommendation(history, seed)

    async def _resolve_spotify_recs(self, data, seed, styles, mood, played_ids):
        provider = settings.LAVALINK_CONFIG.get("SEARCH_PROVIDER", "ytsearch")
        tasks = [wavelink.Playable.search(f"{provider}:{rec}") for rec in data["recs"]]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        candidates = [res[0] for res in results if isinstance(res, list) and res and res[0].identifier not in played_ids]
        if candidates:
            scored = [(c, self._calculate_score(c, seed, styles, mood, spotify_context=data)) for c in candidates]
            scored.sort(key=lambda x: x[1], reverse=True)
            return scored[0][0]
        return None

    def _get_artist_streak(self, history, author):
        streak = 0
        for t in reversed(history):
            if t.author == author: streak += 1
            else: break
        return streak

    def _get_heuristic_queries(self, provider, author, title, styles, streak):
        clean = music_service.clean_track_title(title)
        queries = [
            f"{provider}:{clean} {author} mix",
            f"{provider}:{author} top tracks" # Sugerencias directas del mismo autor
        ]
        
        peers = self._get_related_known_artists(author)
        if peers:
            p = random.choice(peers)
            queries.extend([f"{provider}:{p} top hits", f"{provider}:{p} {self._get_artist_genre(author)}"])

        if styles: queries.append(f"{provider}:{clean} {' '.join(styles)} similar")
        # Si ya hay una racha, buscamos radio; si no, buscamos artistas similares
        queries.append(f"{provider}:{author} {'radio' if streak >= 2 else 'similar artist'}")
        
        if "yt" in provider: queries.append(f"scsearch:{clean} {author} similar")
        return queries

    async def _fetch_candidates(self, queries):
        tasks = [wavelink.Playable.search(q) for q in queries]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        candidates = []
        for res in results:
            if isinstance(res, (list, tuple)): 
                candidates.extend(res[:5])
            elif hasattr(res, 'tracks'): # Manejo robusto de Playlists
                candidates.extend(res.tracks[:5])
                
        return candidates

    def _is_valid_candidate(self, track, p_ids, p_titles, p_authors, streak, seed_author):
        if track.identifier in p_ids: return False
        if any(self._is_similar(track.title, pt) for pt in p_titles): return False
        
        # Si el autor ya sonó recientemente, solo permitimos repetir si es el autor actual
        # para permitir pequeñas rachas (máximo 3 canciones seguidas)
        if track.author.lower() in p_authors:
            if track.author.lower() != seed_author.lower() or streak >= 3:
                return False
        return True

    def _select_best_candidate(self, scored):
        scored.sort(key=lambda x: x[1], reverse=True)
        top = scored[:5]
        weights = [x[1] for x in top]
        tracks = [x[0] for x in top]
        try:
            sel = random.choices(tracks, weights=weights, k=1)[0]
            logger.info(f"🤖 [Algoritmo] Recomendación: {sel.title}")
            return sel
        except: return top[0][0]

    async def _get_fallback_recommendation(self, history, seed):
        if len(history) > 1:
            pool = history[-min(len(history), 50):-1]
            if pool: return random.choice(pool)
        
        try:
            p = settings.LAVALINK_CONFIG.get("SEARCH_PROVIDER", "spsearch")
            res = await wavelink.Playable.search(f"{p}:{random.choice(['lofi hip hop', 'chill mix'])}")
            return res[0] if res else None
        except: return None
