from config import settings
from services.core import db_service, lang_service
from ui import profile_ui

# Re-exportar con envoltura de compatibilidad para HealthCheck/Legacy
async def get_profile_embed(bot, guild, target, lang):
    """Wrapper de compatibilidad para la firma antigua (4 argumentos)."""
    return await handle_profile(guild, target, lang)

async def handle_profile(guild, target, lang):
    """Orquesta la obtención de datos y generación del embed de perfil."""
    user_data = await db_service.fetch_one("SELECT * FROM users WHERE user_id = ?", (target.id,))
    guild_data = await db_service.fetch_one("SELECT xp, level, rebirths FROM guild_stats WHERE guild_id = ? AND user_id = ?", (guild.id, target.id))
    
    nivel = guild_data['level'] if guild_data else 1
    xp_next = db_service.calculate_xp_required(nivel)
    
    return profile_ui.get_profile_embed(target, user_data, guild_data, xp_next, lang)

async def handle_update_description(user_id: int, text: str, lang: str):
    """Maneja la validación y actualización de la descripción."""
    if len(text) > settings.UI_CONFIG["MAX_DESC_LENGTH"]:
        return None, lang_service.get_text("error_max_chars", lang, max=settings.UI_CONFIG["MAX_DESC_LENGTH"])
    
    await db_service.execute(
        "INSERT INTO users (user_id, description) VALUES (?, ?) "
        "ON CONFLICT(user_id) DO UPDATE SET description = excluded.description", 
        (user_id, text)
    )
    return profile_ui.get_profile_update_success_embed(lang, "profile_desc_saved"), None

async def handle_update_personal_message(user_id: int, msg_type: str, text: str, lang: str):
    """Maneja la actualización de mensajes personalizados."""
    val = None if text.lower() == settings.PROFILE_CONFIG["RESET_KEYWORD"] else text
    columna = "personal_level_msg" if msg_type == "Nivel" else "personal_birthday_msg"
    
    query = f"INSERT INTO users (user_id, {columna}) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET {columna} = excluded.{columna}"
    await db_service.execute(query, (user_id, val))
    
    return profile_ui.get_profile_update_success_embed(lang, "profile_msg_saved")