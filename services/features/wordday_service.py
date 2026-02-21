import random
import aiohttp
import asyncio
import html
import discord
import logging
from services.utils import embed_service
from services.core import db_service, lang_service

logger = logging.getLogger(__name__)

# Lista de frases de ejemplo (puedes expandirla o conectarla a una API externa)
PHRASES = [
    "El único modo de hacer un gran trabajo es amar lo que haces. - Steve Jobs",
    "La vida es lo que pasa mientras estás ocupado haciendo otros planes. - John Lennon",
    "No cuentes los días, haz que los días cuenten. - Muhammad Ali",
    "La mente es como un paracaídas, solo funciona si se abre. - Albert Einstein",
    "El éxito es la suma de pequeños esfuerzos repetidos día tras día. - Robert Collier",
    "Tu tiempo es limitado, no lo malgastes viviendo la vida de otro. - Steve Jobs",
    "La mejor forma de predecir el futuro es creándolo. - Peter Drucker",
    "Sé el cambio que quieres ver en el mundo. - Mahatma Gandhi",
    "La felicidad no es algo hecho. Viene de tus propias acciones. - Dalai Lama",
    "Lo que no te mata, te hace más fuerte. - Friedrich Nietzsche"
]

async def _translate(session: aiohttp.ClientSession, text: str, lang_pair: str) -> str:
    """Helper interno para traducir texto usando MyMemory API."""
    url = "https://api.mymemory.translated.net/get"
    params = {"q": text, "langpair": lang_pair}
    try:
        async with session.get(url, params=params, timeout=5) as resp:
            if resp.status == 200:
                data = await resp.json()
                translated = data.get("responseData", {}).get("translatedText", text)
                return html.unescape(translated)
    except Exception as e:
        logger.debug(f"Fallo en traducción ({lang_pair}): {e}")
    return text

async def get_daily_phrase(session: aiohttp.ClientSession):
    """Retorna un diccionario con versiones en inglés y español de la frase del día."""
    url = "https://zenquotes.io/api/random"
    try:
        async with session.get(url, timeout=10) as response:
            if response.status == 200:
                data = await response.json()
                if data and isinstance(data, list):
                    quote = data[0].get("q")
                    author = data[0].get("a")
                    
                    # Traducimos la frase al español usando la misma sesión
                    translated_quote = await _translate(session, quote, "en|es")
                    
                    return {
                        "en": f"{quote} - {author}",
                        "es": f"{translated_quote} - {author}"
                    }
    except Exception as e:
        logger.warning(f"⚠️ No se pudo obtener frase de la API (usando fallback): {e}")
    
    # Fallback: Usamos una frase local (que ya está en español) y la traducimos al inglés
    local_phrase = random.choice(PHRASES)
    translated_local = await _translate(session, local_phrase, "es|en")
    
    return {
        "es": local_phrase,
        "en": translated_local
    }

async def post_wordday(bot: discord.Client):
    """Envía la frase del día a todos los servidores configurados."""
    session = getattr(bot, "session", None)
    if session:
        phrases = await get_daily_phrase(session)
    else:
        async with aiohttp.ClientSession() as session:
            phrases = await get_daily_phrase(session)
    
    # Semáforo para limitar concurrencia y no saturar la API de Discord
    sem = asyncio.Semaphore(10) 

    async def send_to_guild(guild):
        async with sem:
            try:
                config = await db_service.get_guild_config(guild.id)
                channel_id = config.get("wordday_channel_id")
                if not channel_id: return

                channel = guild.get_channel(channel_id)
                if not channel: return

                lang = config.get("language", "es")
                phrase = phrases.get(lang, phrases["es"])
                
                role_id = config.get("wordday_role_id")
                role = guild.get_role(role_id) if role_id else guild.default_role
                mention = role.mention if role else "@everyone"
                
                embed = embed_service.info(lang_service.get_text("wordday_title", lang), f"**{phrase}**")
                embed.set_footer(text=lang_service.get_text("wordday_footer", lang))
                
                await channel.send(content=mention, embed=embed)
            except Exception:
                logger.warning(f"No se pudo enviar frase del día a {guild.name} ({guild.id})")

    # Ejecutar todas las tareas en paralelo
    await asyncio.gather(*(send_to_guild(guild) for guild in bot.guilds))