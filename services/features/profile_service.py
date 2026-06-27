from config import settings
from services.core import db_service, lang_service
from services.repositories.user_repository import UserRepository
from services.repositories.xp_repository import XpRepository, calculate_xp_required
from ui.social import profile_ui

# Re-exportar con envoltura de compatibilidad para HealthCheck/Legacy
async def get_profile_embed(bot, guild, target, lang):
    """Wrapper de compatibilidad para la firma antigua (4 argumentos)."""
    embed, _ = await handle_profile(guild, target, lang, 0)
    return embed

from services.utils.embed_service import NonVitalRenderError

async def handle_profile(guild, target, lang, author_id: int):
    """Orquesta la obtención de datos y generación del embed y vista de perfil."""
    user_data = await UserRepository.get_user_data(target.id)
    
    if guild:
        guild_data = await XpRepository.get_user_guild_data(guild.id, target.id)
    else:
        guild_data = None
    
    nivel = guild_data['level'] if guild_data else 1
    xp_next = calculate_xp_required(nivel)
    
    # Obtener y resolver inventario
    inventory = await db_service.get_user_inventory(target.id)
    shop_items = await db_service.get_all_shop_items()
    shop_map = {item["item_id"]: item for item in shop_items}
    
    inventory_resolved = []
    for item_id, qty in inventory.items():
        if qty <= 0:
            continue
        item_info = shop_map.get(item_id)
        if item_info:
            emoji = item_info.get("emoji") or "📦"
            name = item_info.get("name_default") or lang_service.get_text(item_info.get("name_key"), lang)
        else:
            emoji = "📦"
            name = item_id.replace("_", " ").title()
            
        inventory_resolved.append({
            "item_id": item_id,
            "quantity": qty,
            "emoji": emoji,
            "name": name
        })
    
    try:
        embed = profile_ui.get_general_embed(target, user_data, lang)
    except NonVitalRenderError as nve:
        view = profile_ui.ProfileView(target, user_data, guild_data, xp_next, inventory_resolved, lang, author_id, is_dm=(guild is None))
        nve.view = view
        raise nve
        
    view = profile_ui.ProfileView(target, user_data, guild_data, xp_next, inventory_resolved, lang, author_id, is_dm=(guild is None))
    return embed, view

async def handle_update_description(user_id: int, text: str, lang: str):
    """Maneja la validación y actualización de la descripción."""
    if len(text) > settings.UI_CONFIG["MAX_DESC_LENGTH"]:
        return None, lang_service.get_text("error_max_chars", lang, max=settings.UI_CONFIG["MAX_DESC_LENGTH"])
    
    await UserRepository.update_description(user_id, text)
    return profile_ui.get_profile_update_success_embed(lang, "profile_desc_saved"), None

async def handle_update_personal_message(user_id: int, msg_type: str, text: str, lang: str):
    """Maneja la actualización de mensajes personalizados."""
    val = None if text.lower() == settings.PROFILE_CONFIG["RESET_KEYWORD"] else text
    await UserRepository.update_personal_message(user_id, msg_type, val)
    return profile_ui.get_profile_update_success_embed(lang, "profile_msg_saved")

async def handle_update_gender(user_id: int, gender: str, lang: str):
    """Maneja la actualización del género del usuario en la base de datos."""
    val = None if gender == "none" else gender
    await UserRepository.update_gender(user_id, val)
    return profile_ui.get_profile_update_success_embed(lang, "profile_gender_saved")