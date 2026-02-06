import os
from dotenv import load_dotenv

load_dotenv()

# 1. Token y Claves
TOKEN = os.getenv("DISCORD_TOKEN")

# Para escalado futuro:
DATABASE_URL = os.getenv("DATABASE_URL") # Ejemplo: postgresql://user:pass@localhost/dbname
REDIS_URL = os.getenv("REDIS_URL")       # Ejemplo: redis://localhost:6379/0
IS_PRODUCTION = os.getenv("PRODUCTION", "False") == "True"

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
        "max_clear_msg": 50,
        "delete_after": 5,
        "timeout_limit": 2419200 # 28 días
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
    "FUN": 0xE91E63,      # Rosa
    "MINECRAFT": 0x2ECC71, # Verde Minecraft
    "BLUE": 0x3498DB,     # Azul Sistema
    "GOLD": 0xF1C40F,     # Dorado Memoria
    "TEAL": 0x1ABC9C,     # Teal Config
    "ORANGE": 0xE67E22    # Naranja Logs
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

# --- 9. CONFIGURACIÓN MINECRAFT ---
MINECRAFT_CONFIG = {
    "ENABLED": True,      # True: Carga el servidor web. False: No inicia el puente.
    "PORT": 5058,         # Puerto para recibir datos del plugin de Minecraft
    "DEFAULT_NAME": "Steve", # Nombre por defecto si el plugin no envía el autor
    "TOKEN": "CAMBIAME_POR_UN_TOKEN_SEGURO", # Token de seguridad para el Bridge
    "MAX_PAYLOAD_SIZE": 51200, # 50KB
    "HOST": "0.0.0.0",
    "MAX_QUEUE_SIZE": 50,
    "PORT_RANGE": 3
}

# --- 10. CONFIGURACIÓN CHAOS ---
CHAOS_CONFIG = {
    "DEFAULT_ENABLED": True,
    "DEFAULT_PROB": 0.01
}

# --- 11. CONFIGURACIÓN ALGORITMO (RECOMENDACIONES) ---
ALGORITHM_CONFIG = {
    "HISTORY_LIMIT": 30,          # Canciones a recordar para no repetir
    "SIMILARITY_THRESHOLD": 0.85, # % de similitud para considerar duplicado
    "DEFAULT_METADATA": "Unknown" # Texto por defecto si falta autor/título
}

# --- 12. CONFIGURACIÓN VISUAL Y TÉCNICA DE MÚSICA ---
MUSIC_CONFIG = {
    "QUEUE_PAGE_SIZE": 10,        # Canciones por página en /queue
    "AUTOCOMPLETE_LIMIT": 10,     # Resultados en autocompletado
    "PROGRESS_BAR_LENGTH": 15,    # Longitud de la barra en /np
    "STREAM_BAR_LENGTH": 15,      # Longitud de la barra para streams
    "CROSSFADE_DURATION": 3000,   # Duración del Fade-In en milisegundos (0 = Desactivado). Ej: 3000 para 3s.
    "VOLUME_STEP": 10,            # Paso de volumen para botones
    "AUTOCOMPLETE_TITLE_LIMIT": 65, # Límite de caracteres para título en búsqueda
    "AUTOCOMPLETE_AUTHOR_LIMIT": 15, # Límite de caracteres para autor en búsqueda
    "FADE_IN_STEPS": 15,          # Pasos para la animación de volumen
    "LOOP_EMOJIS": {
        "TRACK": "🔂",
        "QUEUE": "🔁",
        "OFF": "🔁"
    },
    "BUTTON_EMOJIS": {
        "PAUSE_RESUME": "⏯️",
        "SKIP": "⏭️",
        "STOP": "⏹️",
        "SHUFFLE": "🔀",
        "AUTOPLAY": "♾️",
        "VOL_DOWN": "🔉",
        "VOL_UP": "🔊"
    },
    "PROGRESS_BAR_CHAR": "▬",
    "PROGRESS_BAR_POINTER": "🔘",
    "VOLUME_TOLERANCE": 1,
    "CONTROLS_TIMEOUT": None
}

# --- 11. ASSETS (IMÁGENES / GIFS) ---
ASSETS = {
    "COINFLIP_HEADS": "https://cdn.discordapp.com/emojis/745519235303735376.gif",
    "COINFLIP_TAILS": "https://cdn.discordapp.com/emojis/745519477935964212.gif"
}

# --- 12. CONFIGURACIÓN MÚSICA (LAVALINK) ---
LAVALINK_CONFIG = {
    "HOST": "lavalink.jirayu.net",     # Nodo público más estable
    "PORT": 443,                       # Puerto SSL estándar
    "PASSWORD": "youshallnotpass",   # Contraseña del nodo
    "SECURE": True,                    # True si el puerto es 443/SSL
    "DEFAULT_VOLUME": 50,     # Volumen inicial (0-100)
    "SEARCH_PROVIDER": "yt",  # 'yt' (YouTube), 'sc' (SoundCloud), 'sp' (Spotify - requiere nodo con Lavasrc)
    "INACTIVITY_TIMEOUT": 300, # Segundos para desconectarse si no hay música
    "CACHE_CAPACITY": 100,     # Capacidad del caché de Wavelink
    # Credenciales de Spotify (Opcional)
    "SPOTIFY": {
        "CLIENT_ID": os.getenv("SPOTIFY_CLIENT_ID", ""),
        "CLIENT_SECRET": os.getenv("SPOTIFY_CLIENT_SECRET", "")
    }
}

# Helper para compatibilidad (convierte nombre de color a entero)
def get_color(key: str) -> int:
    return COLORS.get(key.upper(), 0xFFFFFF)

# --- 13. CONFIGURACIÓN BASE DE DATOS ---
DB_CONFIG = {
    "DIR_NAME": "data",
    "FILE_NAME": "database.sqlite3",
    "TEMP_BACKUP_NAME": "temp_backup.sqlite3",
    "RETRIES": 3,
    "RETRY_DELAY": 0.1
}

# --- 14. CONFIGURACIÓN BACKUP ---
BACKUP_CONFIG = {
    "HISTORY_LIMIT": 50,
    "MAX_BACKUPS_TO_KEEP": 3,
    "COOLDOWN_SECONDS": 84600, # ~23.5 horas
    "DM_HISTORY_LIMIT": 20,
    "KEYWORD": "Backup",
    "INTERVAL_HOURS": 12,
    "XP_FLUSH_MINUTES": 5
}

# --- 15. CONFIGURACIÓN UI ---
UI_CONFIG = {
    "PROGRESS_BAR_FILLED": "▰",
    "PROGRESS_BAR_EMPTY": "▱",
    "MAX_DESC_LENGTH": 200, # Descripción de perfil
    "PROFILE_BAR_LENGTH": 10,
    "STATUS_TRUNCATE": 97, # Truncado para select menu de status
    "MSG_PREVIEW_TRUNCATE": 30, # Truncado para preview de mensajes en perfil
    "BAR_LENGTH": 10, # Longitud de barras de progreso genéricas
    "SELECT_DESC_TRUNCATE": 100 # Truncado de descripciones en menús de selección
}

LOG_FILE = os.path.join(BASE_DIR, "data", "discord.log")

# --- 16. CONFIGURACIÓN AYUDA ---
HELP_CONFIG = {
    "EMOJI_MAP": {
        "General": "💡", "Moderacion": "🛡️", "Niveles": "📊",
        "Diversion": "🎲", "Configuracion": "⚙️", "Developer": "💻",
        "Cumpleanos": "🎂", "Roles": "🎭", "Voice": "🎙️", 
        "Perfil": "👤", "Status": "🟢", "Backup": "💾",
        "Usuario": "👤", "Minecraft": "🧱", "Music": "🎵"
    },
    "HOME_EMOJI": "🏠"
}

# --- 17. CONFIGURACIÓN VOZ ---
VOICE_CONFIG = {
    "RECONNECT_BACKOFF": [5, 10, 30] # Segundos entre intentos
}

# --- 18. CONFIGURACIÓN OPTIMIZACIÓN ---
OPTIMIZATION_CONFIG = {
    "FLUSH_INTERVAL": 60,      # Segundos
    "CLEANUP_INTERVAL": 6      # Horas
}

# --- 19. CONFIGURACIÓN DESARROLLADOR ---
DEV_CONFIG = {
    "STATUS_LIMIT": 25,
    "SERVER_LIST_CHUNK_SIZE": 10,
    "MEMORY_TOP_LIMIT": 15
}

# --- 20. CONFIGURACIÓN NIVELES ---
LEVELS_CONFIG = {
    "LEADERBOARD_LIMIT": 50,
    "XP_MULTIPLIER": 100,
    "XP_EXPONENT": 1.2,
    "REBIRTH_LEVEL": 100,
    "MEDALS": ["🥇", "🥈", "🥉"],
    "LEADERBOARD_CHUNK_SIZE": 10
}

# --- 21. CONFIGURACIÓN GENERAL ---
GENERAL_CONFIG = {
    "LARGE_SERVER_THRESHOLD": 1000,
    "DEFAULT_LANG": "es"
}

# --- 22. CONFIGURACIÓN PAGINACIÓN ---
PAGINATION_CONFIG = {
    "TIMEOUT": 120,
    "EMOJIS": {
        "FIRST": "⏮️", "PREV": "◀️", "NEXT": "▶️", "LAST": "⏭️"
    }
}

# --- 23. CONFIGURACIÓN PERFIL ---
PROFILE_CONFIG = {
    "RESET_KEYWORD": "reset"
}

# --- 24. CONFIGURACIÓN ROLES ---
ROLES_CONFIG = {
    "DEFAULT_EMOJI": "✨",
    "DEFAULT_COLOR": "green"
}

# --- 25. CONFIGURACIÓN TIMEOUTS (VISTAS) ---
TIMEOUT_CONFIG = {
    "HELP": 120,
    "BOT_INFO": 120,
    "STATUS_DELETE": 60
}

# --- 26. CONFIGURACIÓN POR DEFECTO (GUILDS) ---
DEFAULT_GUILD_CONFIG = {
    "language": "es",
    "chaos_enabled": 1,
    "chaos_probability": 0.01
}

# --- 27. CONFIGURACIÓN CUMPLEAÑOS ---
BIRTHDAY_CONFIG = {
    "CHECK_INTERVAL_HOURS": 24,
    "CAKE_ICON": "https://emojigraph.org/media/apple/birthday-cake_1f382.png",
    "LIST_LIMIT": 10
}

# --- 28. CONFIGURACIÓN BOTINFO ---
BOTINFO_CONFIG = {
    "EMOJIS": {
        "GENERAL": "📊",
        "SYSTEM": "💻",
        "MEMORY": "🧠",
        "CONFIG": "⚙️"
    },
    "TITLE_EMOJI": "🤖",
    "SELECT_EMOJI": "👇"
}

# --- 29. CONFIGURACIÓN MATEMÁTICA ---
MATH_CONFIG = {
    "OP_MAP": {
        "sumar": "+", "suma": "+", "add": "+", "+": "+", "mas": "+",
        "restar": "-", "resta": "-", "minus": "-", "-": "-", "menos": "-",
        "multiplicacion": "*", "multiplicar": "*", "por": "*", "*": "*", "x": "*",
        "division": "/", "dividir": "/", "div": "/", "/": "/"
    }
}