import discord
from config import settings
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
    
    # Usar el color del bot en el servidor o el azul Discord de marca (0x5865F2)
    color = guild.me.color if guild.me.color.value != 0 else discord.Color(0x5865F2)
    embed = discord.Embed(title=title, color=color)
    
    if guild.icon: embed.set_thumbnail(url=guild.icon.url)
    if guild.banner: embed.set_image(url=guild.banner.url)

    # Fila 1: Información Básica
    embed.add_field(name=lang_service.get_text("serverinfo_owner", lang), value=f"<@{guild.owner_id}>", inline=True)
    embed.add_field(name=lang_service.get_text("serverinfo_id", lang), value=f"`{guild.id}`", inline=True)
    embed.add_field(name=lang_service.get_text("serverinfo_created", lang), value=f"<t:{int(guild.created_at.timestamp())}:D>", inline=True)

    # Fila 2: Información del Servidor (Boosts, Emojis, Verificación)
    verification_map = {
        "none": {"es": "Ninguno", "en": "None", "pt": "Nenhum", "fr": "Aucun"},
        "low": {"es": "Bajo", "en": "Low", "pt": "Baixo", "fr": "Faible"},
        "medium": {"es": "Medio", "en": "Medium", "pt": "Médio", "fr": "Moyen"},
        "high": {"es": "Alto", "en": "High", "pt": "Alto", "fr": "Élevé"},
        "highest": {"es": "Extremo", "en": "Extreme", "pt": "Extremo", "fr": "Maximum"}
    }
    raw_ver = stats.get('verification', 'none')
    ver_txt = verification_map.get(raw_ver, verification_map["none"]).get(lang, "None")
    
    emojis_txt = f"😊 {stats['emojis']} / 👾 {stats['stickers']}"
    boost_tier_txt = f"Tier {stats['tier']} ({stats['boosts']} 🚀)"

    embed.add_field(name=lang_service.get_text("serverinfo_boost_tier", lang), value=boost_tier_txt, inline=True)
    embed.add_field(name=lang_service.get_text("serverinfo_emojis", lang), value=emojis_txt, inline=True)
    embed.add_field(name=lang_service.get_text("serverinfo_verification", lang), value=ver_txt, inline=True)

    # Fila 3: Estadísticas del Servidor
    stats_txt = lang_service.get_text("serverinfo_stats_desc", lang,
        total=guild.member_count, humans=stats['humans'], bots=stats['bots'],
        roles=stats['roles'], boosts=stats['boosts'],
        channels=stats['channels'], cats=stats['cats'],
        text=stats['text'], voice=stats['voice']
    )
    formatted_stats = "\n".join(f"> {line}" for line in stats_txt.split('\n'))
    embed.add_field(name=lang_service.get_text("serverinfo_stats", lang), value=formatted_stats, inline=False)

    # Fila 4: Configuración del Bot
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
    formatted_conf = "\n".join(f"> {line}" for line in conf_txt.split('\n'))
    embed.add_field(name=lang_service.get_text("serverinfo_config", lang), value=formatted_conf, inline=False)

    return embed

def get_translate_embed(orig: str, trans: str, lang: str) -> discord.Embed:
    limit = settings.UI_CONFIG["MSG_PREVIEW_TRUNCATE"]
    txt = lang_service.get_text("trans_result", lang, orig=orig[:limit]+"...", trans=trans)
    return embed_service.success(lang_service.get_text("title_translate", lang), txt)