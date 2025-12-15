from config.locales import LOCALES
from services import db_service

DEFAULT_LANG = "es"

async def get_guild_lang(guild_id: int) -> str:
    """Obtiene el idioma preferido del servidor desde la DB."""
    if not guild_id: return DEFAULT_LANG
    row = await db_service.fetch_one("SELECT language FROM guild_config WHERE guild_id = ?", (guild_id,))
    return row['language'] if row else DEFAULT_LANG

def get_text(key: str, lang: str = "es", **kwargs) -> str:
    """Obtiene y formatea el texto."""
    data = LOCALES.get(lang, LOCALES[DEFAULT_LANG])
    text = data.get(key, key) # Si no existe la key, devuelve la key como texto
    try:
        return text.format(**kwargs)
    except KeyError:
        return text