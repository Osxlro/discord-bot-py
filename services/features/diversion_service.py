import discord
import random
from ui import diversion_ui
from services.utils import random_service, embed_service
from services.integrations import emojimixer_service
from services.core import db_service, lang_service

async def handle_jumbo(emoji_str: str, lang: str):
    try:
        partial = discord.PartialEmoji.from_str(emoji_str)
        if partial.is_custom_emoji():
            return diversion_ui.get_jumbo_embed(lang, partial.name, partial.url), None
        return None, lang_service.get_text("jumbo_error", lang)
    except Exception:
        return None, lang_service.get_text("jumbo_invalid", lang)

def handle_coinflip(lang: str):
    res, url_gif = random_service.obtener_cara_cruz()
    return diversion_ui.get_coinflip_embed(lang, res, url_gif)

def handle_choice(opcion_a: str, opcion_b: str, lang: str):
    eleccion = random_service.elegir_opcion(opcion_a, opcion_b)
    return diversion_ui.get_choice_embed(lang, opcion_a, opcion_b, eleccion)

def handle_emojimix(e1: str, e2: str, lang: str):
    url = emojimixer_service.generar_url_emojimix(e1, e2)
    return diversion_ui.get_emojimix_embed(lang, e1, e2, url)

async def handle_confess(guild_id: int, secreto: str, lang: str):
    config = await db_service.get_guild_config(guild_id)
    channel_id = config.get('confessions_channel_id')
    
    if not channel_id:
        return None, None, lang_service.get_text("confess_error_no_channel", lang)
    
    embed = diversion_ui.get_confess_embed(lang, secreto)
    return channel_id, embed, None

def handle_8ball(pregunta: str, lang: str):
    respuestas = lang_service.get_text("8ball_responses", lang).split("|")
    respuesta = random.choice(respuestas)
    return diversion_ui.get_8ball_embed(lang, pregunta, respuesta)