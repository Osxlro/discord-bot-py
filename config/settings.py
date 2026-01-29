import os
from dotenv import load_dotenv

load_dotenv()

# 1. Token y Claves
TOKEN = os.getenv("DISCORD_TOKEN")
# GEMINI_API_KEY ya no es necesaria, la quitamos para limpieza.

# 2. Rutas
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(BASE_DIR, 'config.json')

# 3. Configuración General
CONFIG = {
    "bot_config": {
        "prefix": "/",
        "version": "3.0.0" # Subimos versión por el cambio de sistema
    }
}

# 4. Paleta de Colores Centralizada (Hexadecimales)
# Puedes cambiar estos códigos para cambiar el tema de todo el bot.
COLORS = {
    "SUCCESS": 0x57F287,  # Verde Discord
    "ERROR": 0xED4245,    # Rojo Discord
    "WARNING": 0xFEE75C,  # Amarillo
    "INFO": 0x5865F2,     # Azul Blurple
    "XP": 0x9B59B6,       # Violeta (Para niveles)
    "FUN": 0xE91E63       # Rosa (Para diversión)
}

# 5. Configuración de Backup
SEND_BACKUP_TO_OWNER = True 

# 6. Icono del Bot (Se actualiza al iniciar)
_BOT_ICON_URL = None

def set_bot_icon(url: str):
    global _BOT_ICON_URL
    _BOT_ICON_URL = url

def get_bot_icon() -> str:
    return _BOT_ICON_URL or ""