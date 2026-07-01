import logging
import os
import json
from services.repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)

# Catálogo dinámico de insignias
BADGES_CATALOG = {}
json_path = "./config/badges.json"
if os.path.exists(json_path):
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            BADGES_CATALOG = {badge["badge_id"]: badge for badge in data}
    except Exception as e:
        logger.error(f"❌ Error cargando catálogo de insignias: {e}")
else:
    logger.warning(f"⚠️ [Badge Service] Archivo no encontrado: {json_path}")

def get_badges_catalog():
    """Retorna el catálogo completo de insignias."""
    return BADGES_CATALOG

async def evaluate_auto_badges(user_id: int, current_badge_ids: list[str]) -> list[str]:
    """Evalúa los requisitos de insignias dinámicamente y las otorga si es necesario."""
    coins = None
    rebirths = None
    
    for badge_id, badge in BADGES_CATALOG.items():
        req = badge.get("requirement")
        if not req:
            continue
            
        badge_type = req.get("type")
        target_val = req.get("value")
        
        if badge_id in current_badge_ids:
            continue
            
        met = False
        if badge_type == "coins":
            if coins is None:
                coins = await UserRepository.get_user_coins(user_id)
            if coins >= target_val:
                met = True
        elif badge_type == "rebirths":
            if rebirths is None:
                rebirths = await UserRepository.get_total_rebirths(user_id)
            if rebirths >= target_val:
                met = True
                
        if met:
            await UserRepository.grant_badge(user_id, badge_id)
            current_badge_ids.append(badge_id)
            
    return current_badge_ids

async def get_resolved_badges(user_id: int, lang: str = "es") -> list[dict]:
    """Obtiene la lista de insignias de un usuario con los nombres y descripciones localizados."""
    badge_ids = await UserRepository.get_user_badges(user_id)
    
    # Auto-evaluar insignias basadas en requisitos
    badge_ids = await evaluate_auto_badges(user_id, badge_ids)
            
    resolved = []
    for b_id in badge_ids:
        badge = BADGES_CATALOG.get(b_id)
        if badge:
            names = badge.get("names", {})
            descs = badge.get("descriptions", {})
            name = names.get(lang, names.get("en", b_id))
            desc = descs.get(lang, descs.get("en", ""))
            resolved.append({
                "badge_id": b_id,
                "emoji": badge.get("emoji", "🏅"),
                "name": name,
                "description": desc
            })
    return resolved

async def get_badges_string(user_id: int) -> str:
    """Retorna una cadena de emojis correspondientes a las insignias del usuario."""
    badge_ids = await UserRepository.get_user_badges(user_id)
    
    # Auto-evaluar insignias basadas en requisitos
    badge_ids = await evaluate_auto_badges(user_id, badge_ids)
        
    emojis = []
    for b_id in badge_ids:
        badge = BADGES_CATALOG.get(b_id)
        if badge:
            emojis.append(badge.get("emoji", "🏅"))
    return " ".join(emojis) if emojis else ""
