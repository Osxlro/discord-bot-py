import random
import logging
import unicodedata
from services.integrations import wordgame_api_service, translator_service

logger = logging.getLogger(__name__)

DIFFICULTY_MAP = {
    "fácil": {"min": 3, "max": 5},
    "medio": {"min": 6, "max": 8},
    "difícil": {"min": 9, "max": 20},
    "cualquiera": {"min": 3, "max": 20}
}

def normalize_word(word: str) -> str:
    """
    Normaliza una palabra convirtiéndola a minúsculas y removiendo acentos,
    pero preservando la letra 'ñ'.
    """
    word = word.lower().strip()
    result = []
    for char in word:
        if char in ('ñ', 'Ñ'):
            result.append('ñ')
        else:
            # Descomponer caracteres con acentos
            normalized = unicodedata.normalize('NFD', char)
            # Filtrar marcas de acentuación
            clean_char = "".join([c for c in normalized if not unicodedata.combining(c)])
            result.append(clean_char)
    return "".join(result)

async def translate_safe(text: str, target_lang: str) -> str:
    """Traductor con control de fallos."""
    if not text or target_lang == "en":
        return text
    try:
        res = await translator_service.traducir(text, target_lang)
        return res["traducido"]
    except Exception as e:
        logger.warning(f"Error al traducir '{text}' al idioma {target_lang}: {e}")
        return text

class HangmanService:
    # Historial de palabras usadas recientemente, organizadas por ID de servidor (guild_id)
    _recently_used_words = {}

    @classmethod
    async def get_word(cls, difficulty: str, category: str, lang: str, guild_id: int | None = None) -> dict | None:
        """
        Obtiene una palabra de la API, la traduce al idioma del servidor si es necesario,
        y genera sus versiones normalizadas, evitando repetir palabras recientemente jugadas en el servidor.
        """
        difficulty = difficulty.lower()
        category = category.lower()
        
        bounds = DIFFICULTY_MAP.get(difficulty, DIFFICULTY_MAP["cualquiera"])
        
        words = await wordgame_api_service.fetch_words(
            category=category,
            min_letters=bounds.get("min"),
            max_letters=bounds.get("max")
        )
        
        # Fallback si no hay palabras con los filtros
        if not words:
            logger.warning(f"No se encontraron palabras con filtros: dif={difficulty}, cat={category}. Reintentando sin filtros.")
            words = await wordgame_api_service.fetch_words()
            
        if not words:
            return None
            
        # Filtrar por palabras usadas recientemente en esta guild
        guild_key = guild_id or 0
        if guild_key not in cls._recently_used_words:
            cls._recently_used_words[guild_key] = []
        recent_list = cls._recently_used_words[guild_key]
        
        filtered_words = [w for w in words if normalize_word(w["word"]) not in recent_list]
        if not filtered_words:
            logger.info(f"Todas las palabras disponibles de la API fueron usadas recientemente en guild {guild_key}. Ignorando filtro temporalmente.")
            filtered_words = words
            
        word_data = random.choice(filtered_words)
        original_word = word_data["word"]
        original_hint = word_data.get("hint", "No hint available.")
        
        # Traducir si el idioma de destino no es inglés
        if lang != "en":
            translated_word = await translate_safe(original_word, lang)
            translated_hint = await translate_safe(original_hint, lang)
        else:
            translated_word = original_word
            translated_hint = original_hint
            
        # Limpiar caracteres raros y normalizar
        translated_word = translated_word.strip()
        normalized_word = normalize_word(translated_word)
        
        # Guardar en el historial de esta guild
        norm_chosen = normalize_word(translated_word)
        if norm_chosen not in recent_list:
            recent_list.append(norm_chosen)
            if len(recent_list) > 30:
                recent_list.pop(0)
                
        return {
            "original_word": original_word,
            "original_hint": original_hint,
            "word": translated_word,
            "hint": translated_hint,
            "normalized_word": normalized_word,
            "category": word_data.get("category", category)
        }

    @staticmethod
    def get_initial_hint(word_normalized: str, guessed_letters: set = None) -> str:
        """
        Retorna una letra al azar de la palabra como pista inicial,
        excluyendo aquellas letras que ya hayan sido adivinadas (si se especifican).
        """
        letters = [c for c in word_normalized if c.isalpha()]
        if guessed_letters:
            letters = [c for c in letters if c not in guessed_letters]
        if not letters:
            return ""
        return random.choice(letters)

    @staticmethod
    def calculate_solo_rewards(won: bool, word_len: int, guessed_ratio: float) -> int:
        """Calcula las monedas a pagar en modo SOLO."""
        if won:
            # Victoria: Recompensa media (20 a 40 monedas según longitud)
            return random.randint(20, 30) + min(word_len, 10)
        else:
            # Derrota: Recompensa baja basada en qué tan cerca estuvo
            return round(guessed_ratio * 10)
