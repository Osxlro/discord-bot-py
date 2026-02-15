import discord
from services import db_service, lang_service, embed_service
from config import settings

async def get_setup_info_embed(guild: discord.Guild, lang: str) -> discord.Embed:
    """Genera un embed detallado con la configuración actual del servidor."""
    config = await db_service.get_guild_config(guild.id)

    def get_ch(cid):
        ch = guild.get_channel(cid)
        return ch.mention if ch else "❌"

    def get_role(rid):
        role = guild.get_role(rid)
        return role.mention if role else "@everyone"

    embed = discord.Embed(
        title=f"⚙️ {lang_service.get_text('serverinfo_config', lang)}",
        color=settings.COLORS["INFO"]
    )
    embed.set_author(name=guild.name, icon_url=guild.icon.url if guild.icon else None)

    ch_desc = (
        f"👋 **Bienvenida:** {get_ch(config.get('welcome_channel_id'))}\n"
        f"🤫 **Confesiones:** {get_ch(config.get('confessions_channel_id'))}\n"
        f"📜 **Logs:** {get_ch(config.get('logs_channel_id'))}\n"
        f"🎂 **Cumpleaños:** {get_ch(config.get('birthday_channel_id'))}\n"
        f"📖 **WordDay:** {get_ch(config.get('wordday_channel_id'))}"
    )
    embed.add_field(name=lang_service.get_text("setup_info_channels", lang), value=ch_desc, inline=False)

    chaos_status = "✅" if config.get("chaos_enabled") else "❌"
    chaos_prob = f"{config.get('chaos_probability', 0.01) * 100:.1f}%"
    
    settings_desc = (
        f"🌐 **Idioma:** {lang_service.get_text('lang_name_' + lang, lang)}\n"
        f"👋 **Despedida:** {'✅' if config.get('server_goodbye_msg') else '❌'}\n"
        f"🔫 **Chaos:** {chaos_status} ({chaos_prob})\n"
        f"📢 **Mención WordDay:** {get_role(config.get('wordday_role_id'))}"
    )
    embed.add_field(name=lang_service.get_text("setup_info_settings", lang), value=settings_desc, inline=False)

    return embed

async def update_guild_setup(guild_id: int, updates: dict, lang: str, label: str, value_display: str) -> discord.Embed:
    """Actualiza la configuración en la DB y retorna un embed de éxito."""
    await db_service.update_guild_config(guild_id, updates)
    msg = lang_service.get_text("setup_desc", lang, type=label, value=value_display)
    return embed_service.success(lang_service.get_text("setup_success", lang), msg)