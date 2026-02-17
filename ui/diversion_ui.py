import discord
from services.utils import embed_service
from services.core import lang_service

def get_jumbo_embed(lang: str, name: str, url: str) -> discord.Embed:
    title = lang_service.get_text("jumbo_title", lang, name=name)
    return embed_service.info(title, "", image=url)

def get_coinflip_embed(lang: str, result: str, url_gif: str) -> discord.Embed:
    title = lang_service.get_text("coinflip_title", lang)
    desc = lang_service.get_text("coinflip_desc", lang, result=result)
    return embed_service.info(title, desc, thumbnail=url_gif, lite=True)

def get_choice_embed(lang: str, a: str, b: str, result: str) -> discord.Embed:
    title = lang_service.get_text("choice_title", lang)
    desc = lang_service.get_text("choice_desc", lang, a=a, b=b, result=result)
    return embed_service.success(title, desc, lite=True)

def get_emojimix_embed(lang: str, e1: str, e2: str, url: str) -> discord.Embed:
    title = lang_service.get_text("emojimix_title", lang)
    return embed_service.info(title, f"{e1} + {e2}", image=url)

def get_confess_embed(lang: str, secreto: str) -> discord.Embed:
    title = lang_service.get_text("confess_title", lang)
    embed = discord.Embed(title=title, description=f"\"{secreto}\"", color=discord.Color.random())
    embed.set_footer(text=lang_service.get_text("confess_anon", lang))
    return embed

def get_8ball_embed(lang: str, pregunta: str, respuesta: str) -> discord.Embed:
    title = lang_service.get_text("eightball_title", lang)
    return embed_service.info(title, f"**P:** {pregunta}\n**R:** {respuesta}", lite=True)