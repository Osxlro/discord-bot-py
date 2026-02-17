import discord
from services.utils import embed_service
from services.core import lang_service

def get_ping_embed(ms: int, lang: str) -> discord.Embed:
    txt = lang_service.get_text("ping_msg", lang, ms=ms)
    return embed_service.info(lang_service.get_text("title_ping", lang), txt, lite=True)

def get_calc_success_embed(num1: float, op_symbol: str, num2: float, res: float, lang: str) -> discord.Embed:
    txt = lang_service.get_text("calc_result", lang, a=num1, op=op_symbol, b=num2, res=res)
    return embed_service.success(lang_service.get_text("title_math", lang), txt)

def get_serverinfo_embed(guild: discord.Guild, config: dict, stats: dict, lang: str) -> discord.Embed:
    title = lang_service.get_text("serverinfo_title", lang, name=guild.name)
    embed = discord.Embed(title=title, color=guild.me.color)
    
    if guild.icon: embed.set_thumbnail(url=guild.icon.url)
    if guild.banner: embed.set_image(url=guild.banner.url)

    # Información General
    embed.add_field(name=lang_service.get_text("serverinfo_owner", lang), value=f"<@{guild.owner_id}>", inline=True)
    embed.add_field(name=lang_service.get_text("serverinfo_id", lang), value=f"`{guild.id}`", inline=True)
    embed.add_field(name=lang_service.get_text("serverinfo_created", lang), value=f"<t:{int(guild.created_at.timestamp())}:D>", inline=True)

    # Estadísticas
    stats_txt = lang_service.get_text("serverinfo_stats_desc", lang,
        total=guild.member_count, humans=stats['humans'], bots=stats['bots'],
        roles=stats['roles'], boosts=stats['boosts'],
        channels=stats['channels'], cats=stats['cats'],
        text=stats['text'], voice=stats['voice']
    )
    embed.add_field(name=lang_service.get_text("serverinfo_stats", lang), value=stats_txt, inline=False)

    # Configuración
    def fmt(val, type_):
        if not val: return lang_service.get_text("serverinfo_not_set", lang)
        return f"<#{val}>" if type_ == "ch" else f"<@&{val}>"

    lang_key = f"lang_name_{config.get('language', 'es')}"
    lang_name = lang_service.get_text(lang_key, lang)
    
    conf_txt = lang_service.get_text("serverinfo_conf_desc", lang,
        language=lang_name,
        welcome=fmt(config.get("welcome_channel_id"), "ch"),
        confess=fmt(config.get("confessions_channel_id"), "ch"),
        logs=fmt(config.get("logs_channel_id"), "ch"),
        bday=fmt(config.get("birthday_channel_id"), "ch"),
        autorole=fmt(config.get("autorole_id"), "role")
    )
    embed.add_field(name=lang_service.get_text("serverinfo_config", lang), value=conf_txt, inline=False)

    return embed

def get_translate_embed(orig: str, trans: str, lang: str) -> discord.Embed:
    from config import settings
    limit = settings.UI_CONFIG["MSG_PREVIEW_TRUNCATE"]
    txt = lang_service.get_text("trans_result", lang, orig=orig[:limit]+"...", trans=trans)
    return embed_service.success(lang_service.get_text("title_translate", lang), txt)