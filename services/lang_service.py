from config.locales import LOCALES

DEFAULT_LANG = "es"

def get_text(key: str, lang: str = "es", **kwargs) -> str:
    """
    Obtiene un texto y rellena las variables.
    Ej: get_text("ping_msg", ms=120)
    """
    # Si el idioma no existe, usa default
    idioma_data = LOCALES.get(lang, LOCALES[DEFAULT_LANG])
    
    # Si la clave no existe, devuelve la clave como error visual
    texto = idioma_data.get(key, key)
    
    # Rellena las variables {ms}, {user}, etc.
    try:
        return texto.format(**kwargs)
    except KeyError:
        return texto # Si faltan variables, devolvemos el texto sin formatear para no romper