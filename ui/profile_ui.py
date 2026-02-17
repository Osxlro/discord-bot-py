import discord
from config import settings
from services.core import lang_service
from services.utils import embed_service

def get_profile_embed(target: discord.Member, user_data: dict, guild_data: dict, xp_next: int, lang: str) -> discord.Embed:
    """Construye el embed del perfil del usuario con los datos proporcionados."""
    # Datos globales del usuario
    desc = user_data['description'] if user_data else lang_service.get_text("profile_desc", lang)
    cumple = user_data['birthday'] if user_data and user_data['birthday'] else lang_service.get_text("profile_no_bday", lang)
    prefix = user_data['custom_prefix'] if user_data and user_data['custom_prefix'] else settings.CONFIG["bot_config"]["prefix"]
    
    # Estadísticas específicas del servidor
    xp = guild_data['xp'] if guild_data else 0
    nivel = guild_data['level'] if guild_data else 1
    rebirths = guild_data['rebirths'] if guild_data else 0
    
    # Cálculo de la barra de progreso
    progreso = min(xp / xp_next, 1.0) if xp_next > 0 else 1.0
    bar_len = settings.UI_CONFIG["PROFILE_BAR_LENGTH"]
    bloques = int(progreso * bar_len)
    barra = settings.UI_CONFIG["PROGRESS_BAR_FILLED"] * bloques + settings.UI_CONFIG["PROGRESS_BAR_EMPTY"] * (bar_len - bloques)

    # Construcción del Embed
    title = lang_service.get_text("profile_title", lang, user=target.display_name)
    embed = discord.Embed(title=title, color=target.color)
    embed.set_thumbnail(url=target.display_avatar.url)
    
    embed.add_field(name=lang_service.get_text("profile_field_desc", lang), value=f"*{desc}*", inline=False)
    embed.add_field(name=lang_service.get_text("profile_field_bday", lang), value=f"{cumple}", inline=True)
    embed.add_field(name=lang_service.get_text("profile_field_prefix", lang), value=f"`{prefix}`", inline=True)
    
    stats_title = lang_service.get_text("profile_server_stats", lang)
    embed.add_field(name="⠀", value=stats_title, inline=False)
    
    embed.add_field(name=lang_service.get_text("profile_field_lvl", lang), value=f"**{nivel}**", inline=True)
    embed.add_field(name=lang_service.get_text("profile_field_rebirths", lang), value=f"**{rebirths}**", inline=True)
    embed.add_field(name=lang_service.get_text("profile_field_xp", lang), value=f"{xp}", inline=True)
    
    progress_label = lang_service.get_text("profile_progress", lang, percent=int(progreso*100))
    embed.add_field(name=progress_label, value=f"`{barra}` {xp}/{xp_next}", inline=False)

    # Previsualización de mensajes personalizados
    msgs = ""
    if user_data:
        limit = settings.UI_CONFIG["MSG_PREVIEW_TRUNCATE"]
        if user_data['personal_level_msg']: 
            msgs += lang_service.get_text("profile_preview_lvl", lang, msg=user_data['personal_level_msg'][:limit]) + "\n"
        if user_data['personal_birthday_msg']: 
            msgs += lang_service.get_text("profile_preview_bday", lang, msg=user_data['personal_birthday_msg'][:limit]) + "\n"
    
    if msgs:
        embed.add_field(name=lang_service.get_text("profile_custom_msgs", lang), value=msgs, inline=False)

    return embed

def get_profile_update_success_embed(lang: str, type_key: str) -> discord.Embed:
    """Genera un embed de éxito para actualizaciones de perfil."""
    title = lang_service.get_text("profile_update_success", lang)
    desc = lang_service.get_text(type_key, lang)
    return embed_service.success(title, desc, lite=True)