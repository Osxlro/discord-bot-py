import logging
from services.repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)

# Catálogo estático de insignias
BADGES_CATALOG = {
    "pioneer": {
        "emoji": "🌐",
        "names": {"es": "Pionero de la Web", "en": "Web Pioneer", "pt": "Pioneiro da Web", "fr": "Pionnier du Web"},
        "descs": {
            "es": "Por registrarse e iniciar sesión en el portal web.",
            "en": "For registering and logging in on the web portal.",
            "pt": "Por registrar-se e fazer login no portal web.",
            "fr": "Pour s'être inscrit et connecté sur le portail web."
        }
    },
    "rich": {
        "emoji": "💰",
        "names": {"es": "Capitalista", "en": "Capitalist", "pt": "Capitalista", "fr": "Capitaliste"},
        "descs": {
            "es": "Otorgado al acumular más de 5,000 monedas en tu cartera.",
            "en": "Awarded for accumulating more than 5,000 coins in your wallet.",
            "pt": "Concedido ao acumular mais de 5.000 moedas na sua carteira.",
            "fr": "Attribué pour avoir accumulé plus de 5 000 pièces dans votre portefeuille."
        }
    },
    "first_rebirth": {
        "emoji": "🌀",
        "names": {"es": "Primer Renacimiento", "en": "First Rebirth", "pt": "Primeiro Renascimento", "fr": "Premier Rebirth"},
        "descs": {
            "es": "Otorgado al realizar tu primer renacimiento (rebirth) en el servidor.",
            "en": "Awarded for performing your first rebirth in the server.",
            "pt": "Concedido ao realizar seu primeiro renascimento no servidor.",
            "fr": "Attribué pour avoir effectué votre premier rebirth sur le serveur."
        }
    },
    "bug_hunter": {
        "emoji": "🐛",
        "names": {"es": "Cazador de Bugs", "en": "Bug Hunter", "pt": "Caçador de Bugs", "fr": "Chasseur de Bugs"},
        "descs": {
            "es": "Otorgado por reportar errores y ayudar a mejorar el bot.",
            "en": "Awarded for reporting bugs and helping to improve the bot.",
            "pt": "Concedido por reportar erros e ajudar a melhorar o bot.",
            "fr": "Attribué pour avoir signalé des bogues et aidé à améliorer le bot."
        }
    }
}

async def get_resolved_badges(user_id: int, lang: str = "es") -> list[dict]:
    """Obtiene la lista de insignias de un usuario con los nombres y descripciones localizados."""
    badge_ids = await UserRepository.get_user_badges(user_id)
    
    # Auto-evaluar insignias basadas en monedas
    coins = await UserRepository.get_user_coins(user_id)
    if coins >= 5000:
        if "rich" not in badge_ids:
            await UserRepository.grant_badge(user_id, "rich")
            badge_ids.append("rich")
            
    resolved = []
    for b_id in badge_ids:
        badge = BADGES_CATALOG.get(b_id)
        if badge:
            name = badge["names"].get(lang, badge["names"]["en"])
            desc = badge["descs"].get(lang, badge["descs"]["en"])
            resolved.append({
                "badge_id": b_id,
                "emoji": badge["emoji"],
                "name": name,
                "description": desc
            })
    return resolved

async def get_badges_string(user_id: int) -> str:
    """Retorna una cadena de emojis correspondientes a las insignias del usuario."""
    badge_ids = await UserRepository.get_user_badges(user_id)
    
    # Auto-evaluar monedas
    coins = await UserRepository.get_user_coins(user_id)
    if coins >= 5000 and "rich" not in badge_ids:
        await UserRepository.grant_badge(user_id, "rich")
        badge_ids.append("rich")
        
    emojis = []
    for b_id in badge_ids:
        badge = BADGES_CATALOG.get(b_id)
        if badge:
            emojis.append(badge["emoji"])
    return " ".join(emojis) if emojis else ""
