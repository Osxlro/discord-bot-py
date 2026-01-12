import os
import json
from dotenv import load_dotenv

load_dotenv()

# 1. Token (Seguridad)
TOKEN = os.getenv("DISCORD_TOKEN")

# 2. Rutas
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(BASE_DIR, 'config.json')

# 3. Cargador de Configuración
def load_config():
    """Carga el archivo config.json y retorna un diccionario"""
    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print("❌ CRÍTICO: No se encontró config.json en la raíz.")
        return {}
    except json.JSONDecodeError:
        print("❌ CRÍTICO: El archivo config.json tiene errores de sintaxis.")
        return {}

# Variable global que importaremos en otros archivos
CONFIG = load_config()
_BOT_ICON_URL = None

# Acceso rápido a colores (opcional, para escribir menos código luego)
# Convierte el string hex "0x..." a entero para Discord
def get_color(category: str):
    hex_str = CONFIG.get("colors", {}).get(category, "0xFFFFFF")
    return int(hex_str, 16)

def set_bot_icon(url: str):
    """Guarda la URL del icono del bot en memoria."""
    global _BOT_ICON_URL
    _BOT_ICON_URL = url

def get_bot_icon() -> str:
    """Recupera la URL guardada (o None si aún no se ha guardado)."""
    return _BOT_ICON_URL

# DM BACKUP
SEND_BACKUP_TO_OWNER = True  # Cambia a False si no quieres recibir el DM con la DB