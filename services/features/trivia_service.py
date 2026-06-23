from services.utils import http_client
import random
import asyncio
import logging
from services.integrations import translator_service
from services.core import lang_service

logger = logging.getLogger(__name__)

async def fetch_trivia_question(lang: str) -> dict | None:
    """
    Obtiene una pregunta de Trivia desde la API pública y traduce sus componentes
    al idioma del servidor actual si es necesario.
    """
    url = "https://the-trivia-api.com/v2/questions?limit=1"
    
    try:
        data = await http_client.fetch_json(url, timeout=10)
        if not data or not isinstance(data, list):
            return None
        
        question_data = data[0]

                
        # Extraer datos originales
        original_text = question_data["question"]["text"]
        original_correct = question_data["correctAnswer"]
        original_incorrect = question_data["incorrectAnswers"]
        category = question_data.get("category", "general")
        difficulty = question_data.get("difficulty", "medium")
        
        # Traducir si el idioma de destino no es inglés
        if lang != "en":
            # Traducir pregunta y respuesta correcta
            task_q = translate_text(original_text, lang)
            task_c = translate_text(original_correct, lang)
            
            # Traducir las respuestas incorrectas concurrentemente
            tasks_inc = [translate_text(ans, lang) for ans in original_incorrect]
            
            translated_q, translated_c, *translated_inc = await asyncio.gather(
                task_q, task_c, *tasks_inc
            )
        else:
            translated_q = original_text
            translated_c = original_correct
            translated_inc = original_incorrect

        # Mezclar las opciones
        options = translated_inc + [translated_c]
        random.shuffle(options)
        
        # Buscar el índice de la respuesta correcta
        correct_index = options.index(translated_c)
        
        return {
            "question": translated_q,
            "options": options,
            "correct_index": correct_index,
            "correct_answer": translated_c,
            "category": category,
            "difficulty": difficulty
        }
    except Exception as e:
        logger.exception(f"Error fetching/translating trivia question: {e}")
        return None


async def translate_text(text: str, target_lang: str) -> str:
    """Traductor seguro con fallback en caso de error."""
    try:
        res = await translator_service.traducir(text, target_lang)
        return res["traducido"]
    except Exception as e:
        logger.warning(f"No se pudo traducir '{text}' al idioma {target_lang}: {e}")
        return text
