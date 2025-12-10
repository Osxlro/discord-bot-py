def generar_url_emojimix(emoji1: str, emoji2: str) -> str:
    """
    Genera la URL para mezclar dos emojis usando una API pública.
    Nota: No todos los emojis son compatibles.
    """
    # Esta API gratuita mezcla emojis al estilo Google Emoji Kitchen
    return f"https://emojik.vercel.app/s/{emoji1}_{emoji2}?size=128"