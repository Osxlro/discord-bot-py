import discord
import random
from ui import diversion_ui
from services.utils import random_service, embed_service
from services.core import db_service, lang_service
from services.integrations import emojimixer_service, nekos_api_service

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

async def handle_anime(lang: str):
    """
    Obtiene una imagen anime aleatoria desde el servicio NekosAPI
    y construye el embed con la descripción correspondiente.
    """
    image_data = await nekos_api_service.get_random_image(rating="safe")
    if not image_data:
        return None, lang_service.get_text("anime_error_fetch", lang)

    url = image_data.get("url")
    artist = image_data.get("artist_name")
    source = image_data.get("source_url")
    tags = image_data.get("tags", [])

    desc_parts = []
    if artist:
        lbl_artist = lang_service.get_text("anime_lbl_artist", lang)
        desc_parts.append(f"> **🎨 {lbl_artist}:** {artist}")
    if source:
        lbl_source = lang_service.get_text("anime_lbl_source", lang)
        desc_parts.append(f"> **🔗 {lbl_source}:** [Pixiv/Source]({source})")
    if tags:
        lbl_tags = lang_service.get_text("anime_lbl_tags", lang)
        tags_str = ", ".join(f"`{t}`" for t in tags[:5])
        desc_parts.append(f"> **🏷️ {lbl_tags}:** {tags_str}")

    description = "\n".join(desc_parts) if desc_parts else ""
    
    # Generar Kaomoji aleatorio en el título
    kaomojis = ["(◕‿◕)", "(´• ω •`)", "(つ✧ω✧)つ", "(o^▽^o)", "(≧◡≦)", "(⌒‿⌒)", "(^人^)", "(✿◠‿◠)", "(｀▽´)", "(◕‿◕✿)", "(*^ω^*)"]
    kaomoji = random.choice(kaomojis)
    title = f"Anime {kaomoji}"
    
    embed = diversion_ui.get_anime_embed(lang, url, description, title=title)
    return embed, None