import asyncio
from deep_translator import GoogleTranslator

def _traducir_sync(texto: str, idioma_destino: str) -> str:
    """Función síncrona (bloqueante) interna."""
    translator = GoogleTranslator(source='auto', target=idioma_destino)
    return translator.translate(texto)

async def traducir(texto: str, idioma_destino: str = 'es') -> dict:
    """
    Función asíncrona pública.
    Ejecuta la traducción en un hilo separado para no bloquear el bot.
    """
    try:
        # Enviamos la tarea pesada a un hilo aparte
        traduccion = await asyncio.to_thread(_traducir_sync, texto, idioma_destino)
        
        return {
            "original": texto,
            "traducido": traduccion,
            "idioma": idioma_destino
        }
    except Exception as e:
        raise ValueError(f"Error al conectar con el servicio de traducción: {str(e)}")