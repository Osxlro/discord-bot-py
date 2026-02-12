import random
import asyncio
import aiohttp
import base64
import time
import re
import wavelink
import logging
import datetime
from difflib import SequenceMatcher
from config import settings
from services import db_service, music_service

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
        # Palabras clave para detectar "Vibra" o Estilo
        self.style_keywords = [
            "nightcore", "daycore", "lo-fi", "lofi", "remix", "acoustic", 
            "live", "cover", "instrumental", "slowed", "reverb", "bassboost",
            "speed up", "8d", "mashup"
        ]
        
        # --- CONFIGURACIÓN DE MOODS TEMPORALES ---
        self.MOODS = {
            "late_night": {"genres": ["indie", "acoustic", "lofi", "jazz"], "energy_range": (0.0, 0.4)},
            "morning": {"genres": ["pop", "indie", "acoustic"], "energy_range": (0.3, 0.6)},
            "day": {"genres": ["pop", "rock", "hiphop", "reggaeton"], "energy_range": (0.6, 1.0)},
            "evening": {"genres": ["rock", "edm", "hiphop", "metal"], "energy_range": (0.5, 0.9)}
        }

        # --- BIBLIOTECA DE CURACIÓN MUSICAL (Knowledge Base) ---
        # Mapeo de géneros a artistas "Safe/Known" para asegurar calidad
        self.GENRE_MAP = {
            "pop": ["Taylor Swift", "The Weeknd", "Dua Lipa", "Ariana Grande", "Justin Bieber", "Bruno Mars", "Ed Sheeran"],
            "rock": ["Queen", "Arctic Monkeys", "The Rolling Stones", "Nirvana", "Linkin Park", "Imagine Dragons", "Coldplay"],
            "reggaeton": ["Bad Bunny", "J Balvin", "Karol G", "Rauw Alejandro", "Feid", "Daddy Yankee", "Ozuna"],
            "hiphop": ["Drake", "Kendrick Lamar", "Kanye West", "Travis Scott", "Eminem", "Post Malone", "Doja Cat"],
            "edm": ["Avicii", "David Guetta", "Calvin Harris", "Daft Punk", "Skrillex", "Marshmello", "Tiësto"],
            "indie": ["Tame Impala", "The Killers", "Lana Del Rey", "The 1975", "Florence + The Machine"],
            "metal": ["Metallica", "AC/DC", "Guns N' Roses", "Slipknot", "System of a Down", "Rammstein"]
        }
        
        # Lista plana de artistas conocidos para scoring rápido
        self.KNOWN_ARTISTS = {artist.lower() for artists in self.GENRE_MAP.values() for artist in artists}
        
        # Configuración Spotify (Opcional)
        self.sp_client_id = settings.LAVALINK_CONFIG["SPOTIFY"]["CLIENT_ID"]
        self.sp_client_secret = settings.LAVALINK_CONFIG["SPOTIFY"]["CLIENT_SECRET"]
        self.sp_token = None
        self.sp_token_expiry = 0

    async def _get_spotify_token(self):
        """Obtiene un token de acceso para la API de Spotify."""
        if not self.sp_client_id or not self.sp_client_secret: return None
        if self.sp_token and time.time() < self.sp_token_expiry: return self.sp_token

        try:
            auth = base64.b64encode(f"{self.sp_client_id}:{self.sp_client_secret}".encode()).decode()
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://accounts.spotify.com/api/token",
                    headers={"Authorization": f"Basic {auth}"},
                    data={"grant_type": "client_credentials"}
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        self.sp_token = data["access_token"]
                        self.sp_token_expiry = time.time() + data["expires_in"] - 60
                        return self.sp_token
                    else:
                        error_body = await resp.text()
                        logger.error(f"❌ [Spotify API] Error de Token ({resp.status}): {error_body}")
        except Exception:
            logger.exception("⚠️ Error obteniendo token Spotify")
        return None

    async def _get_spotify_context(self, seed_track: wavelink.Playable) -> dict:
        """Obtiene recomendaciones y características de audio de Spotify."""
        token = await self._get_spotify_token()
        if not token: return {}

        clean_title = music_service.clean_track_title(seed_track.title)
        query = f"{clean_title} {seed_track.author}"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://api.spotify.com/v1/search",
                headers={"Authorization": f"Bearer {token}"},
                params={"q": query, "type": "track", "limit": 1}
            ) as resp:
                if resp.status != 200:
                    error_body = await resp.text()
                    logger.error(f"❌ [Spotify API] Error en búsqueda ({resp.status}): {error_body}")
                    return {}
                data = await resp.json()
                if not data["tracks"]["items"]: return {}
                track_data = data["tracks"]["items"][0]
                spotify_id = track_data["id"]

            # Obtener Audio Features (Energía, Valencia, etc.)
            async with session.get(
                f"https://api.spotify.com/v1/audio-features/{spotify_id}",
                headers={"Authorization": f"Bearer {token}"}
            ) as resp:
                features = await resp.json() if resp.status == 200 else {}

            # Pedir recomendaciones quirúrgicas
            mood = self._get_current_mood()
            params = {
                "seed_tracks": spotify_id,
                "limit": 8,
                "target_energy": features.get("energy", self.MOODS[mood]["energy_range"][1]),
                "target_valence": features.get("valence", 0.5)
            }

            async with session.get(
                "https://api.spotify.com/v1/recommendations",
                headers={"Authorization": f"Bearer {token}"},
                params=params
            ) as resp:
                if resp.status != 200:
                    error_body = await resp.text()
                    logger.error(f"❌ [Spotify API] Error en recomendaciones ({resp.status}): {error_body}")
                    return {"features": features, "recs": []}
                data = await resp.json()
                recs = [f"{t['name']} - {t['artists'][0]['name']}" for t in data["tracks"]]
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

    def _calculate_score(self, candidate: wavelink.Playable, seed: wavelink.Playable, seed_styles: set[str], feedback: dict = None, spotify_context: dict = None) -> int:
        """Asigna una puntuación de relevancia al candidato (0-100+)."""
        score = 100
        
        # 1. Análisis de Estilo (Vibe Check)
        cand_styles = self._get_style_tags(candidate.title)
        
        # Si la semilla tiene estilo (ej: Nightcore) y el candidato NO, penalización fuerte.
        if seed_styles and not cand_styles:
            score -= 40
        # Si comparten estilos, bonificación.
        common_styles = seed_styles & cand_styles
        score += len(common_styles) * 15
        
        # 2. Bono por Artista Conocido (Crucial para evitar "relleno")
        cand_author = candidate.author.lower()
        if any(known in cand_author for known in self.KNOWN_ARTISTS):
            score += 60
            
        # 3. Bono por Mood Temporal
        mood = self._get_current_mood()
        cand_genre = self._get_artist_genre(candidate.author)
        if cand_genre in self.MOODS[mood]["genres"]:
            score += 25

        # 2. Análisis de Duración
        # Evitar saltos bruscos (ej: de canción de 3min a mix de 1 hora)
        diff_ms = abs(candidate.length - seed.length)
        if diff_ms > 600000: # Diferencia > 10 min
            score -= 30
        elif diff_ms < 60000: # Diferencia < 1 min (muy similar duración es bueno)
            score += 10
            
        # 3. Penalización por "Video Oficial" vs Audio
        # A veces queremos variedad, no solo el video oficial si ya escuchamos el audio
        if "official video" in candidate.title.lower() and "official video" in seed.title.lower():
            score -= 5 # Leve penalización para buscar variedad visual/audio
            
        # 4. Penalización por "Live" si la original no lo era
        if "live" in candidate.title.lower() and "live" not in seed.title.lower():
            score -= 25

        # 5. Lógica de Covers
        is_cover_seed = "cover" in seed.title.lower()
        is_cover_cand = "cover" in candidate.title.lower()
        
        if is_cover_seed and is_cover_cand and candidate.author.lower() == seed.author.lower():
            score -= 80 # No queremos dos covers seguidos del mismo artista de covers
            
        # 6. Coherencia Lingüística (Heurística simple)
        is_spanish_seed = any(w in seed.title.lower() for w in [" de ", " la ", " el ", " con "])
        is_spanish_cand = any(w in candidate.title.lower() for w in [" de ", " la ", " el ", " con "])
        if is_spanish_seed != is_spanish_cand:
            score -= 20 # Penalizar cambio de idioma brusco
            
        # 5. Inteligencia Local (Feedback del Servidor)
        if feedback:
            plays = feedback.get('plays', 0)
            skips = feedback.get('skips', 0)
            if plays > 0 or skips > 0:
                # Ratio de éxito: más plays = más puntos, más skips = menos puntos.
                success_rate = plays / (plays + skips + 1)
                # Ajuste de hasta +/- 50 puntos basado en la experiencia previa del servidor
                score += int((success_rate - 0.5) * 100)

        return max(0, score)

    async def get_recommendation(self, player: wavelink.Player) -> wavelink.Playable:
        if not player.queue.history:
            return None

        # 1. Contexto Histórico
        history = list(player.queue.history)
        recent_tracks = history[-self.history_limit:]
        
        # Lista negra de IDs y Títulos para evitar repeticiones
        played_ids = {t.identifier for t in recent_tracks}
        played_titles = [t.title for t in recent_tracks]
        played_authors = {t.author.lower() for t in recent_tracks}

        # Semilla Principal (Última canción)
        seed_track = history[-1]
        author = seed_track.author or settings.ALGORITHM_CONFIG["DEFAULT_METADATA"]
        title = seed_track.title or settings.ALGORITHM_CONFIG["DEFAULT_METADATA"]
        seed_styles = self._get_style_tags(title)
        
        # --- ESTRATEGIA 1: SPOTIFY (INTELIGENCIA REAL) ---
        # Prioridad absoluta: Si Spotify está configurado, lo usamos.
        spotify_data = await self._get_spotify_context(seed_track)
        spotify_recs = spotify_data.get("recs", [])
        
        if spotify_recs:
            logger.info(f"🧠 [Algoritmo] Procesando {len(spotify_recs)} recomendaciones de Spotify...")
            
            # Intentamos resolver las recomendaciones usando el proveedor preferido (Spotify)
            # Solo si falla el proveedor principal, permitimos el fallback a YouTube para el audio.
            primary_provider = settings.LAVALINK_CONFIG.get("SEARCH_PROVIDER", "spsearch")
            
            tasks = [wavelink.Playable.search(f"{primary_provider}:{rec}") for rec in spotify_recs]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            candidates = []
            for res in results:
                if isinstance(res, list) and res:
                    candidates.append(res[0])
            
            valid_candidates = [c for c in candidates if c.identifier not in played_ids]
            
            if valid_candidates:
                logger.info(f"✅ [Algoritmo] Recomendación resuelta vía: {primary_provider}")
                scored = [(c, self._calculate_score(c, seed_track, seed_styles, spotify_context=spotify_data)) for c in valid_candidates]
                scored.sort(key=lambda x: x[1], reverse=True)
                return scored[0][0]
            else:
                logger.warning("⚠️ Spotify no pudo resolver el audio de sus propias recomendaciones. Saltando a Heurística.")

        # --- ESTRATEGIA 2: HEURÍSTICA V2 (FALLBACK) ---
        provider = settings.LAVALINK_CONFIG.get("SEARCH_PROVIDER", "spsearch")
        
        # Si Spotify no está disponible (sin token), forzamos el fallback manual a YouTube
        if not self.sp_token and provider == "spsearch":
            provider = "ytsearch"
            
        # Si Spotify falla o no está configurado, usamos el motor lógico.
        
        # Detección de Racha de Artista (¿El usuario quiere escuchar solo a este artista?)
        artist_streak = 0
        for t in reversed(history):
            if t.author == author: artist_streak += 1
            else: break
        
        # Generación de Estrategias (Queries)
        queries = []
        clean_title = music_service.clean_track_title(title)

        # A. Estrategia "Radio/Mix" (Base)
        queries.append(f"{provider}:{clean_title} {author} mix")
        
        # B. Estrategia "Conocidos del mismo Género" (NUEVO)
        related_peers = self._get_related_known_artists(author)
        if related_peers:
            peer = random.choice(related_peers)
            queries.append(f"{provider}:{peer} top hits")
            queries.append(f"{provider}:{peer} {self._get_artist_genre(author)}")

        # C. Estrategia "Continuidad de Estilo"
        if seed_styles:
            style_str = " ".join(seed_styles)
            queries.append(f"{provider}:{clean_title} {style_str} similar")
        
        # D. Estrategia "Descubrimiento vs Profundidad"
        if artist_streak >= 3:
            # El usuario está obsesionado con este artista, démosle más
            queries.append(f"{provider}:{author} best songs")
        else:
            # Variedad: Artistas similares (Búsqueda abierta)
            queries.append(f"{provider}:{author} similar artist")
            
        # D. Fallback (SoundCloud si usamos YT, para evitar bloqueos)
        if "yt" in provider:
            queries.append(f"scsearch:{clean_title} {author} similar")

        # 3. Búsqueda Paralela
        tasks = [wavelink.Playable.search(q) for q in queries]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        candidates = []
        for res in results:
            if isinstance(res, list):
                candidates.extend(res[:5]) # Tomamos top 5 de cada estrategia
            elif isinstance(res, wavelink.Playlist):
                candidates.extend(res.tracks[:5])

        # 3.5 Obtener Feedback de la DB para todos los candidatos (Carga masiva)
        ids = [c.identifier for c in candidates]
        server_feedback = await db_service.get_bulk_feedback(player.guild.id, ids)

        # 4. Filtrado y Puntuación (El Cerebro)
        scored_candidates = []
        
        for track in candidates:
            # Filtro ID
            if track.identifier in played_ids:
                continue
            
            # Filtro Título (Fuzzy)
            is_duplicate = False
            for played_title in played_titles:
                if self._is_similar(track.title, played_title):
                    is_duplicate = True
                    break
            if is_duplicate:
                continue
            
            # Penalizar si el artista ya sonó hace poco (a menos que sea racha)
            if track.author.lower() in played_authors and artist_streak < 2:
                continue

            # Calcular Score
            track_feedback = server_feedback.get(track.identifier)
            score = self._calculate_score(track, seed_track, seed_styles, track_feedback, spotify_context=spotify_data)
            scored_candidates.append((track, score))

        # 5. Selección Ponderada
        if scored_candidates:
            # Ordenamos por score descendente
            scored_candidates.sort(key=lambda x: x[1], reverse=True)
            
            # Tomamos los mejores 5 (Top Tier)
            top_tier = scored_candidates[:5]
            
            # Selección aleatoria ponderada dentro del top tier para variedad
            # (Si el score es muy alto, tiene más probabilidad, pero no es determinista)
            weights = [x[1] for x in top_tier]
            tracks = [x[0] for x in top_tier]
            
            try:
                # random.choices devuelve una lista, tomamos el primero
                selected = random.choices(tracks, weights=weights, k=1)[0]
                logger.info(f"🤖 [Algoritmo] Recomendación: {selected.title} (Score: {next(s for t, s in top_tier if t == selected)})")
                return selected
            except (IndexError, ValueError):
                return top_tier[0][0] # Fallback al mejor absoluto
            
        logger.warning(f"⚠️ No se encontraron recomendaciones válidas para: {seed_track.title}")

        # --- FALLBACK: REPRODUCCIÓN HISTÓRICA (AUTO-DJ) ---
        # Si el algoritmo falla, reproducimos algo del historial para mantener la música sonando.
        if len(history) > 1:
            # Evitamos la última canción (seed_track) para no repetir inmediatamente
            # Tomamos una muestra aleatoria de las últimas 50 canciones
            pool = history[-min(len(history), 50):-1]
            if pool:
                fallback = random.choice(pool)
                logger.info(f"🔄 [Algoritmo] Fallback Histórico: {fallback.title}")
                return fallback

        # --- ÚLTIMO RECURSO: BÚSQUEDA GENÉRICA ---
        # Si todo falla, buscamos algo popular para no romper el flujo
        try:
            provider = settings.LAVALINK_CONFIG.get("SEARCH_PROVIDER", "spsearch")
            fallback_queries = ["lofi hip hop radio", "top hits 2024", "chill mix"]
            gen_recs = await wavelink.Playable.search(f"{provider}:{random.choice(fallback_queries)}")
            if gen_recs:
                return gen_recs[0]
        except:
            return None
