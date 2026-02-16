from config import settings
from services.core import db_service
from ui.profile_ui import get_profile_embed

async def update_description(user_id: int, text: str):
    """Actualiza la descripción global del usuario."""
    await db_service.execute("INSERT INTO users (user_id, description) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET description = excluded.description", (user_id, text))

async def update_personal_message(user_id: int, msg_type: str, text: str):
    """Actualiza o resetea un mensaje personalizado (Nivel o Cumpleaños)."""
    val = None if text.lower() == settings.PROFILE_CONFIG["RESET_KEYWORD"] else text
    columna = "personal_level_msg" if msg_type == "Nivel" else "personal_birthday_msg"
    
    query = f"INSERT INTO users (user_id, {columna}) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET {columna} = excluded.{columna}"
    await db_service.execute(query, (user_id, val))