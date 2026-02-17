import discord
import logging
from ui import general_ui
from services.core import db_service, lang_service
from services.integrations import translator_service
from config import settings

logger = logging.getLogger(__name__)

async def handle_ping(bot: discord.Client, lang: str):
    ms = round(bot.latency * 1000)
    return general_ui.get_ping_embed(ms, lang)

async def handle_calc(operacion: str, num1: float, num2: float, lang: str):
    op_symbol = settings.MATH_CONFIG["OP_MAP"].get(operacion.lower())
    if not op_symbol:
        return None, lang_service.get_text("calc_error_invalid_op", lang)
    
    try:
        res = 0
        if op_symbol == "+": res = num1 + num2
        elif op_symbol == "-": res = num1 - num2
        elif op_symbol == "*": res = num1 * num2
        elif op_symbol == "/":
            if num2 == 0: raise ValueError(lang_service.get_text("math_div_zero", lang))
            res = round(num1 / num2, 2)
        
        return general_ui.get_calc_success_embed(num1, op_symbol, num2, res, lang), None
    except ValueError as e:
        return None, lang_service.get_text("calc_error", lang, error=str(e))

async def handle_serverinfo(guild: discord.Guild, lang: str):
    config = await db_service.get_guild_config(guild.id)
    
    stats = {
        'roles': len(guild.roles),
        'boosts': guild.premium_subscription_count,
        'channels': len(guild.channels),
        'cats': len(guild.categories),
        'text': len(guild.text_channels),
        'voice': len(guild.voice_channels)
    }

    if guild.member_count > settings.GENERAL_CONFIG["LARGE_SERVER_THRESHOLD"]:
        na = lang_service.get_text("serverinfo_na", lang)
        stats['humans'], stats['bots'] = na, na
    else:
        stats['humans'] = len([m for m in guild.members if not m.bot])
        stats['bots'] = guild.member_count - stats['humans']
    
    return general_ui.get_serverinfo_embed(guild, config, stats, lang)

async def handle_translate(content: str, lang: str):
    try:
        res = await translator_service.traducir(content, settings.GENERAL_CONFIG["DEFAULT_LANG"])
        return general_ui.get_translate_embed(content, res['traducido'], lang), None
    except Exception:
        logger.exception("Error Traductor")
        return None, lang_service.get_text("trans_error", lang)