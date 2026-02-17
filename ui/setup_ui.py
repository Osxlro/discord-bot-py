import discord
from services.utils import embed_service
from services.core import lang_service

def get_setup_success_embed(lang: str, label: str, value: str) -> discord.Embed:
    """Genera un embed simple de éxito para cambios de configuración."""
    title = lang_service.get_text("setup_success", lang)
    desc = lang_service.get_text("setup_desc", lang, type=label, value=value)
    return embed_service.success(title, desc, lite=True)

def get_setup_info_embed(guild: discord.Guild, config: dict, lang: str) -> discord.Embed:
    """Genera un embed detallado con toda la configuración del servidor."""
    embed = discord.Embed(
        title=f"{lang_service.get_text('serverinfo_config', lang)} - {guild.name}",
        color=discord.Color.blue()
    )
    
    def fmt(val, type_):
        if not val or val == 0: return lang_service.get_text("serverinfo_not_set", lang)
        return f"<#{val}>" if type_ == "ch" else f"<@&{val}>"

    # Sección de Canales
    channels_title = lang_service.get_text("setup_info_channels", lang)
    channels_desc = (
        f"👋 **Welcome:** {fmt(config.get('welcome_channel_id'), 'ch')}\n"
        f"🤫 **Confessions:** {fmt(config.get('confessions_channel_id'), 'ch')}\n"
        f"📜 **Logs:** {fmt(config.get('logs_channel_id'), 'ch')}\n"
        f"🎂 **Birthday:** {fmt(config.get('birthday_channel_id'), 'ch')}\n"
        f"📖 **WordDay:** {fmt(config.get('wordday_channel_id'), 'ch')}\n"
        f"🧱 **Minecraft:** {fmt(config.get('minecraft_channel_id'), 'ch')}"
    )
    embed.add_field(name=channels_title, value=channels_desc, inline=False)

    # Sección de Ajustes
    settings_title = lang_service.get_text("setup_info_settings", lang)
    
    # Mapeo de nombres de idioma localizados
    lang_map = {
        "es": lang_service.get_text("lang_name_es", lang),
        "en": lang_service.get_text("lang_name_en", lang),
        "pt": lang_service.get_text("lang_name_pt", lang),
        "fr": lang_service.get_text("lang_name_fr", lang)
    }
    current_lang = lang_map.get(config.get("language", "es"), "Unknown")
    
    chaos_status = "✅" if config.get("chaos_enabled") else "❌"
    chaos_prob = config.get("chaos_probability", 0.01) * 100
    
    settings_desc = (
        f"🌐 **Language:** {current_lang}\n"
        f"🔫 **Chaos:** {chaos_status} ({chaos_prob}%)\n"
        f"🎭 **Auto-Rol:** {fmt(config.get('autorole_id'), 'role')}\n"
        f"🏷️ **WordDay Role:** {fmt(config.get('wordday_role_id'), 'role')}"
    )
    embed.add_field(name=settings_title, value=settings_desc, inline=False)
    
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
        
    return embed