import random
import asyncio
import wavelink
import logging
from difflib import SequenceMatcher
from config import settings

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

    def _is_similar(self, a: str, b: str) -> bool:
        """Compara dos títulos y devuelve True si son casi idénticos."""
        return SequenceMatcher(None, a.lower(), b.lower()).ratio() > self.similarity_threshold

    def _get_style_tags(self, title: str) -> set[str]:
        """Extrae etiquetas de estilo del título."""
        if not title: return set()
        return {tag for tag in self.style_keywords if tag in title.lower()}

    def _calculate_score(self, candidate: wavelink.Playable, seed: wavelink.Playable, seed_styles: set[str]) -> int:
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

        # Semilla Principal (Última canción)
        seed_track = history[-1]
        author = seed_track.author or settings.ALGORITHM_CONFIG["DEFAULT_METADATA"]
        title = seed_track.title or settings.ALGORITHM_CONFIG["DEFAULT_METADATA"]
        seed_styles = self._get_style_tags(title)

        # Detección de Racha de Artista (¿El usuario quiere escuchar solo a este artista?)
        artist_streak = 0
        for t in reversed(history):
            if t.author == author: artist_streak += 1
            else: break
        
        # 2. Generación de Estrategias (Queries)
        provider = settings.LAVALINK_CONFIG.get("SEARCH_PROVIDER", "yt")
        queries = []

        # A. Estrategia "Radio/Mix" (Base)
        queries.append(f"{provider}search:{title} {author} mix")
        
        # B. Estrategia "Continuidad de Estilo"
        if seed_styles:
            style_str = " ".join(seed_styles)
            queries.append(f"{provider}search:{title} {style_str} similar")
        
        # C. Estrategia "Descubrimiento vs Profundidad"
        if artist_streak >= 3:
            # El usuario está obsesionado con este artista, démosle más
            queries.append(f"{provider}search:{author} best songs")
        else:
            # Variedad: Artistas similares
            queries.append(f"{provider}search:{author} similar artist")
            
        # D. Fallback (SoundCloud si usamos YT, para evitar bloqueos)
        if provider == "yt":
            queries.append(f"scsearch:{title} {author} similar")

        # 3. Búsqueda Paralela
        tasks = [wavelink.Playable.search(q) for q in queries]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        candidates = []
        for res in results:
            if isinstance(res, list):
                candidates.extend(res[:5]) # Tomamos top 5 de cada estrategia
            elif isinstance(res, wavelink.Playlist):
                candidates.extend(res.tracks[:5])

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
            
            # Calcular Score
            score = self._calculate_score(track, seed_track, seed_styles)
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
        return None
