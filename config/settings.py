import os
from dotenv import load_dotenv

load_dotenv()

# 1. Token y Claves
TOKEN = os.getenv("DISCORD_TOKEN")

# 2. Rutas
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 3. Configuración General del Bot
CONFIG = {
    "bot_config": {
        "prefix": "!",
        "version": "3.1.0",
        "description": "Oscurin Inc"
    },
    # Configuración de Moderación (Usada en cogs/moderacion.py)
    "moderation_config": {
        "max_clear_msg": 50
    }
}

# --- 4. CONFIGURACIÓN DE JUEGO (GAMEPLAY / XP) ---
# ¡Ajusta esto para cambiar la dificultad del servidor!
XP_CONFIG = {
    "MIN_XP": 15,          # Mínimo de XP por mensaje
    "MAX_XP": 25,          # Máximo de XP por mensaje
    "COOLDOWN": 60.0,      # Segundos de espera entre mensajes para ganar XP
    "VOICE_AMOUNT": 15,    # XP ganada por intervalo en voz
    "VOICE_INTERVAL": 300  # Segundos para ganar XP en voz (300s = 5 minutos)
}

# --- 5. PERMISOS Y SEGURIDAD ---
# True: Solo TÚ (Owner) puedes usar /setup status.
# False: TÚ y los ADMINISTRADORES pueden usarlo.
STATUS_COMMAND_ONLY_OWNER = False 

# Configuración de Backup (DM)
SEND_BACKUP_TO_OWNER = True 

# --- 6. APARIENCIA (COLORES) ---
# Paleta de colores centralizada
COLORS = {
    "SUCCESS": 0x57F287,  # Verde Discord
    "ERROR": 0xED4245,    # Rojo Discord
    "INFO": 0x5865F2,     # Azul Blurple
    "WARNING": 0xFEE75C,  # Amarillo
    "XP": 0x9B59B6,       # Violeta
    "FUN": 0xE91E63       # Rosa
}

# --- 7. ESTADOS POR DEFECTO ---
# Si la base de datos de estados se vacía, se pueden usar estos.
DEFAULT_STATUSES = [
    {"type": "playing", "text": "Visual Studio Code"},
    {"type": "watching", "text": "a los usuarios"},
    {"type": "listening", "text": "tus comandos /"}
]

# --- 8. GESTIÓN DE ICONO ---
_BOT_ICON_URL = None

def set_bot_icon(url: str):
    global _BOT_ICON_URL
    _BOT_ICON_URL = url

def get_bot_icon() -> str:
    return _BOT_ICON_URL or ""

# Helper para compatibilidad (convierte nombre de color a entero)
def get_color(key: str) -> int:
    return COLORS.get(key.upper(), 0xFFFFFF)