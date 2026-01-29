from config import locales, settings
from services import db_service

DEFAULT_LANG = "es"

async def get_guild_lang(guild_id: int) -> str:
    """
    Obtiene el idioma del servidor usando el CACHÉ.
    Súper rápido ⚡
    """
    # Usamos la nueva función optimizada
    config = await db_service.get_guild_config(guild_id)
    
    # Si la config existe y tiene idioma, lo retornamos, si no, default
    return config.get("language", DEFAULT_LANG)

def get_text(key: str, lang: str = "es", **kwargs) -> str:
    """
    Obtiene un texto traducido y formatea las variables.
    Ej: get_text("welcome", user="Juan")
    """
    # Si el idioma no existe, fallback a Español
    if lang not in locales.LOCALES:
        lang = "es"
    
    # Obtener diccionario del idioma
    lang_dict = locales.LOCALES[lang]
    
    # Obtener texto
    text = lang_dict.get(key, f"Missing key: {key}")
    
    # Formatear si hay variables
    if kwargs:
        try:
            return text.format(**kwargs)
        except Exception as e:
            return text # Retornar sin formato si falla
            
    return text