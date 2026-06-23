import discord
from services.utils import embed_service
from services.core import lang_service

def get_join_success_embed(lang: str, channel_name: str) -> discord.Embed:
    """Genera el embed de éxito al unirse a un canal."""
    msg = lang_service.get_text("voice_join", lang, channel=channel_name)
    return embed_service.success(lang_service.get_text("voice_title", lang), msg, lite=True)

def get_leave_success_embed(lang: str) -> discord.Embed:
    """Genera el embed de éxito al salir de un canal."""
    msg = lang_service.get_text("voice_leave", lang)
    return embed_service.success(lang_service.get_text("voice_title", lang), msg, lite=True)

def get_voice_error_embed(lang: str, key: str) -> discord.Embed:
    """Genera un embed de error para acciones de voz."""
    msg = lang_service.get_text(key, lang)
    return embed_service.error(lang_service.get_text("title_error", lang), msg)