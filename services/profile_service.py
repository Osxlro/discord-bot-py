import discord
from config import settings
from services import db_service, lang_service

async def get_profile_embed(bot: discord.Client, guild: discord.Guild, target: discord.Member, lang: str) -> discord.Embed:
    """Recupera datos y construye el embed del perfil del usuario."""
    # Recuperamos datos de las tablas correspondientes
    user_data = await db_service.fetch_one("SELECT * FROM users WHERE user_id = ?", (target.id,))
    guild_data = await db_service.fetch_one("SELECT xp, level, rebirths FROM guild_stats WHERE guild_id = ? AND user_id = ?", (guild.id, target.id))

    # Datos globales del usuario
    desc = user_data['description'] if user_data else lang_service.get_text("profile_desc", lang)
    cumple = user_data['birthday'] if user_data and user_data['birthday'] else lang_service.get_text("profile_no_bday", lang)
    prefix = user_data['custom_prefix'] if user_data and user_data['custom_prefix'] else settings.CONFIG["bot_config"]["prefix"]
    
    # Estadísticas específicas del servidor
    xp = guild_data['xp'] if guild_data else 0
    nivel = guild_data['level'] if guild_data else 1
    rebirths = guild_data['rebirths'] if guild_data else 0
    
    # Cálculo de la barra de progreso
    xp_next = db_service.calculate_xp_required(nivel)
    progreso = min(xp / xp_next, 1.0)
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
    
    embed.add_field(name=f"Progress ({int(progreso*100)}%)", value=f"`{barra}` {xp}/{xp_next}", inline=False)

    # Previsualización de mensajes personalizados
    msgs = ""
    if user_data:
        limit = settings.UI_CONFIG["MSG_PREVIEW_TRUNCATE"]
        if user_data['personal_level_msg']: msgs += lang_service.get_text("profile_preview_lvl", lang, msg=user_data['personal_level_msg'][:limit]) + "\n"
        if user_data['personal_birthday_msg']: msgs += lang_service.get_text("profile_preview_bday", lang, msg=user_data['personal_birthday_msg'][:limit]) + "\n"
    
    if msgs:
        embed.add_field(name=lang_service.get_text("profile_custom_msgs", lang), value=msgs, inline=False)

    return embed

async def update_description(user_id: int, text: str):
    """Actualiza la descripción global del usuario."""
    await db_service.execute("INSERT INTO users (user_id, description) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET description = excluded.description", (user_id, text))

async def update_personal_message(user_id: int, msg_type: str, text: str):
    """Actualiza o resetea un mensaje personalizado (Nivel o Cumpleaños)."""
    val = None if text.lower() == settings.PROFILE_CONFIG["RESET_KEYWORD"] else text
    columna = "personal_level_msg" if msg_type == "Nivel" else "personal_birthday_msg"
    
    query = f"INSERT INTO users (user_id, {columna}) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET {columna} = excluded.{columna}"
    await db_service.execute(query, (user_id, val))