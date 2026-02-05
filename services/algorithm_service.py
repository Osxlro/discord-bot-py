import random
import asyncio
import wavelink
import logging
from difflib import SequenceMatcher
from config import settings

logger = logging.getLogger(__name__)

class RecommendationEngine:
    """
    Motor de recomendaciones inteligente para el sistema de música.
    Utiliza heurística y comparación de cadenas para evitar repeticiones.
    """
    
    def __init__(self):
        self.history_limit = 30 # Recordar últimas 30 canciones para no repetir
        self.similarity_threshold = 0.85 # Si el título se parece un 85%, es la misma canción

    def _is_similar(self, a: str, b: str) -> bool:
        """Compara dos títulos y devuelve True si son casi idénticos."""
        return SequenceMatcher(None, a.lower(), b.lower()).ratio() > self.similarity_threshold

    async def get_recommendation(self, player: wavelink.Player) -> wavelink.Playable:
        if not player.queue.history:
            return None

        # 1. Obtener contexto (Historial reciente)
        # Convertimos el historial a una lista para indexar
        history = list(player.queue.history)
        recent_tracks = history[-self.history_limit:]
        
        # Lista negra de IDs y Títulos para evitar repeticiones
        played_ids = {t.identifier for t in recent_tracks}
        played_titles = [t.title for t in recent_tracks]

        # 2. Seleccionar Semilla (Seed)
        # Usamos la última canción como referencia principal
        seed_track = history[-1]
        
        # 3. Generar Estrategias de Búsqueda (Queries)
        # Buscamos variedad: Mix del artista, canciones similares, etc.
        author = seed_track.author or "Unknown"
        title = seed_track.title or "Unknown"
        
        # Usamos el proveedor configurado en settings (yt, sc, sp)
        provider = settings.LAVALINK_CONFIG.get("SEARCH_PROVIDER", "yt")
        queries = [
            f"{provider}search:{title} {author}", # Búsqueda principal
        ]
        
        # Si usamos YT, añadimos SC como respaldo por si YT falla (tu error actual)
        if provider == "yt":
            queries.append(f"scsearch:{title} {author}")
        
        # Si hay suficiente historial, intentamos mezclar con el penúltimo artista para variar
        if len(history) > 1:
            prev_track = history[-2]
            if prev_track.author != author:
                queries.append(f"{provider}search:{prev_track.author} {author} mix")

        # 4. Ejecución Paralela (Optimización de velocidad)
        # Lanzamos todas las búsquedas a la vez en lugar de una por una
        tasks = [wavelink.Playable.search(q) for q in queries]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        candidates = []
        for res in results:
            if isinstance(res, list):
                # Tomamos los primeros 3 de cada búsqueda para tener candidatos de calidad
                candidates.extend(res[:3])
            elif isinstance(res, wavelink.Playlist):
                candidates.extend(res.tracks[:3])

        # 5. Filtrado Inteligente (El cerebro del algoritmo)
        valid_candidates = []
        
        for track in candidates:
            # A. Filtro de ID exacto
            if track.identifier in played_ids:
                continue
            
            # B. Filtro de Título (Fuzzy Matching)
            # Evita: "Song A" vs "Song A (Official Video)" vs "Song A (Live)"
            is_duplicate = False
            for played_title in played_titles:
                if self._is_similar(track.title, played_title):
                    is_duplicate = True
                    break
            
            if is_duplicate:
                continue
                
            valid_candidates.append(track)

        # 6. Selección Final
        if valid_candidates:
            # Barajamos los candidatos válidos para dar sensación de aleatoriedad
            return random.choice(valid_candidates)
            
        logger.warning(f"⚠️ No se encontraron recomendaciones válidas para: {seed_track.title}")
        return None
