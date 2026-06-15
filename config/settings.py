import os
from dotenv import load_dotenv

load_dotenv()

# =============================================================================
# 1. NÚCLEO Y ENTORNO (CORE)
# =============================================================================
TOKEN = os.getenv("DISCORD_TOKEN")  # Token principal del bot de Discord
DATABASE_URL = os.getenv("DATABASE_URL")  # URL para DB externa (PostgreSQL/MySQL)
REDIS_URL = os.getenv("REDIS_URL")  # URL para servidor de caché Redis
IS_PRODUCTION = os.getenv("PRODUCTION", "True") == "True"  # Flag de entorno de producción
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # Ruta raíz del proyecto
LOG_FILE = os.path.join(BASE_DIR, "data", "discord.log")  # Ruta del archivo de logs

# =============================================================================
# 2. IDENTIDAD Y ESTADO DEL BOT
# =============================================================================
CONFIG = {
    "bot_config": {
        "prefix": "=",  # Prefijo para comandos de mensaje (Legacy)
        "version": "1.5",  # Versión actual del bot
        "description": "Oscurin Inc",  # Descripción general
        "presence_asset": "seor"  # Nombre del asset en el Developer Portal
    },
    "moderation_config": {
        "max_clear_msg": 50,  # Límite de mensajes para /clear
        "delete_after": 5,  # Segundos antes de borrar confirmaciones de moderación
        "timeout_limit": 2419200,  # Límite máximo de aislamiento (28 días en seg)
        "warns_page_size": 5  # Advertencias por página en /warns
    }
}

DEFAULT_STATUSES = [  # Estados de respaldo si la DB está vacía
    {"type": "playing", "text": "Visual Studio Code"},
    {"type": "watching", "text": "a los usuarios"},
    {"type": "listening", "text": "tus comandos /"}
]

_BOT_ICON_URL = None  # Almacena la URL del avatar del bot en caché

def set_bot_icon(url: str):
    """Establece la URL del icono del bot."""
    global _BOT_ICON_URL
    _BOT_ICON_URL = url

def get_bot_icon() -> str:
    """Obtiene la URL del icono del bot."""
    return _BOT_ICON_URL or ""

# =============================================================================
# 3. SISTEMA DE MÚSICA (LAVALINK)
# =============================================================================
LAVALINK_CONFIG = {
    "NODES": [  # Pool de nodos para redundancia y failover
        {"HOST": "lavalink.jirayu.net", "PORT": 13592, "PASSWORD": "youshallnotpass", "SECURE": False, "IDENTIFIER": "Jirayu-NonSSL"},
        {"HOST": "lavalinkv4.serenetia.com", "PORT": 80, "PASSWORD": "https://dsc.gg/ajidevserver", "SECURE": False, "IDENTIFIER": "Serenetia-NonSSL"},
        {"HOST": "lavalinkv4.serenetia.com", "PORT": 443, "PASSWORD": "https://dsc.gg/ajidevserver", "SECURE": True, "IDENTIFIER": "Serenetia-SSL"},
        {"HOST": "lavalink.jirayu.net", "PORT": 443, "PASSWORD": "youshallnotpass", "SECURE": True, "IDENTIFIER": "Jirayu-SSL"},
    ],
    "DEFAULT_VOLUME": 50,  # Volumen por defecto al conectar
    "SEARCH_PROVIDER": "spsearch",  # Proveedor: 'spsearch' (Spotify), 'ytsearch' (YouTube) o 'scsearch' (SoundCloud)
    "INACTIVITY_TIMEOUT": 300,  # Tiempo para desconectar si el canal está vacío
    "CACHE_CAPACITY": 100,  # Límite de canciones en el caché de Wavelink
    "SPOTIFY": {  # Credenciales para soporte de links de Spotify
        "CLIENT_ID": os.getenv("SPOTIFY_CLIENT_ID", ""),
        "CLIENT_SECRET": os.getenv("SPOTIFY_CLIENT_SECRET", "")
    }
}

MUSIC_CONFIG = {
    "QUEUE_PAGE_SIZE": 10,  # Canciones por página en el comando /queue
    "AUTOCOMPLETE_LIMIT": 10,  # Máximo de sugerencias en el buscador
    "PROGRESS_BAR_LENGTH": 15,  # Bloques de la barra de progreso en /np
    "STREAM_BAR_LENGTH": 15,  # Bloques de la barra para directos
    "CROSSFADE_DURATION": 3000,  # Milisegundos de desvanecimiento al iniciar pista
    "VOLUME_STEP": 10,  # Cuánto sube/baja el volumen con botones
    "AUTOCOMPLETE_TITLE_LIMIT": 65,  # Truncado de título en autocompletado
    "AUTOCOMPLETE_AUTHOR_LIMIT": 15,  # Truncado de autor en autocompletado
    "FADE_IN_STEPS": 15,  # Suavidad de la animación de volumen
    "LOOP_EMOJIS": {"TRACK": "🔂", "QUEUE": "🔁", "OFF": "🔁"},
    "BUTTON_EMOJIS": {
        "PREVIOUS": "⏮️", "PAUSE_RESUME": "⏯️", "SKIP": "⏭️", "QUEUE": "📜", "STOP": "⏹️", "SHUFFLE": "🔀",
        "AUTOPLAY": "♾️", "VOL_DOWN": "🔉", "VOL_UP": "🔊", "LYRICS": "📝"
    },
    "SOURCE_EMOJIS": {
        "youtube": "🔴",
        "spotify": "🟢",
        "soundcloud": "🟠",
        "unknown": "🎵"
    },
    "PROGRESS_BAR_CHAR": "▬",
    "PROGRESS_BAR_POINTER": "🔘",
    "VOLUME_TOLERANCE": 1,  # Margen para detectar cambios manuales de volumen
    "CONTROLS_TIMEOUT": None  # Tiempo de vida de los botones (None = Infinito)
}

ALGORITHM_CONFIG = {
    "HISTORY_LIMIT": 30,  # Canciones a recordar para evitar repeticiones en Autoplay
    "SIMILARITY_THRESHOLD": 0.85,  # % de similitud para detectar duplicados
    "DEFAULT_METADATA": "Unknown",  # Texto si no se encuentra autor/título
    "STYLE_KEYWORDS": [
        "nightcore", "daycore", "lo-fi", "lofi", "remix", "acoustic", 
        "live", "cover", "instrumental", "slowed", "reverb", "bassboost",
        "speed up", "8d", "mashup"
    ],
    "MOODS": {
        "late_night": {"genres": ["indie", "acoustic", "lofi", "jazz"], "energy_range": (0.0, 0.4)},
        "morning": {"genres": ["pop", "indie", "acoustic"], "energy_range": (0.3, 0.6)},
        "day": {"genres": ["pop", "rock", "hiphop", "reggaeton"], "energy_range": (0.6, 1.0)},
        "evening": {"genres": ["rock", "edm", "hiphop", "metal"], "energy_range": (0.5, 0.9)}
    },
    "GENRE_MAP": {
        "pop": ["Taylor Swift", "The Weeknd", "Dua Lipa", "Ariana Grande", "Justin Bieber", "Bruno Mars", "Ed Sheeran"],
        "rock": ["Queen", "Arctic Monkeys", "The Rolling Stones", "Nirvana", "Linkin Park", "Imagine Dragons", "Coldplay"],
        "reggaeton": ["Bad Bunny", "J Balvin", "Karol G", "Rauw Alejandro", "Feid", "Daddy Yankee", "Ozuna"],
        "hiphop": ["Drake", "Kendrick Lamar", "Kanye West", "Travis Scott", "Eminem", "Post Malone", "Doja Cat"],
        "edm": ["Avicii", "David Guetta", "Calvin Harris", "Daft Punk", "Skrillex", "Marshmello", "Tiësto"],
        "indie": ["Tame Impala", "The Killers", "Lana Del Rey", "The 1975", "Florence + The Machine"],
        "metal": ["Metallica", "AC/DC", "Guns N' Roses", "Slipknot", "System of a Down", "Rammstein"]
    }
}

# =============================================================================
# 4. GAMEPLAY Y SISTEMA DE NIVELES (XP)
# =============================================================================
XP_CONFIG = {
    "MIN_XP": 15,  # XP mínima por mensaje
    "MAX_XP": 25,  # XP máxima por mensaje
    "COOLDOWN": 60.0,  # Segundos entre mensajes para ganar XP
    "VOICE_AMOUNT": 15,  # XP por intervalo en canal de voz
    "VOICE_INTERVAL": 300  # Intervalo de tiempo para XP en voz (5 min)
}

LEVELS_CONFIG = {
    "LEADERBOARD_LIMIT": 50,  # Máximo de usuarios en el top
    "XP_MULTIPLIER": 100,  # Multiplicador base para la curva de nivel
    "XP_EXPONENT": 1.2,  # Exponente de dificultad de nivel
    "REBIRTH_LEVEL": 100,  # Nivel necesario para renacer
    "MEDALS": ["🥇", "🥈", "🥉"],  # Emojis para el podio
    "LEADERBOARD_CHUNK_SIZE": 10,  # Usuarios por página en el leaderboard
    "REBIRTH_COST": 100,  # Costo en monedas para hacer rebirth
    "COINS_PER_LEVEL": (5, 10)  # Monedas ganadas por nivel subido (mínimo, máximo)
}

# =============================================================================
# 5. BASE DE DATOS Y PERSISTENCIA
# =============================================================================
DB_CONFIG = {
    "DIR_NAME": "data",  # Carpeta de la base de datos
    "FILE_NAME": "database.sqlite3",  # Nombre del archivo SQLite
    "TEMP_BACKUP_NAME": "temp_backup.sqlite3",  # Nombre temporal para backups
    "RETRIES": 3,  # Reintentos si la DB está bloqueada
    "RETRY_DELAY": 0.1  # Segundos entre reintentos
}

BACKUP_CONFIG = {
    "HISTORY_LIMIT": 50,  # Mensajes a revisar para buscar backups antiguos
    "MAX_BACKUPS_TO_KEEP": 3,  # Cuántos archivos de backup mantener en el DM
    "COOLDOWN_SECONDS": 84600,  # Tiempo entre backups automáticos
    "DM_HISTORY_LIMIT": 20,  # Límite de mensajes al limpiar el DM del owner
    "KEYWORD": "Backup",  # Palabra clave para identificar mensajes de backup
    "INTERVAL_HOURS": 12,  # Frecuencia de backups automáticos
    "XP_FLUSH_MINUTES": 5  # Frecuencia para volcar XP de RAM a Disco
}

SEND_BACKUP_TO_OWNER = True  # Enviar copia de seguridad al dueño del bot

# =============================================================================
# 6. INTEGRACIONES EXTERNAS (MINECRAFT)
# =============================================================================
MINECRAFT_CONFIG = {
    "ENABLED": True,  # Activar/Desactivar el servidor web del bridge
    "PORT": 5058,  # Puerto de escucha para el plugin
    "DEFAULT_NAME": "Steve",  # Nombre por defecto para el chat
    "TOKEN": "CAMBIAME_POR_UN_TOKEN_SEGURO",  # Token de validación para peticiones
    "MAX_PAYLOAD_SIZE": 51200,  # Tamaño máximo de datos recibidos (50KB)
    "HOST": "0.0.0.0",  # Interfaz de red
    "MAX_QUEUE_SIZE": 50,  # Mensajes pendientes para enviar al juego
    "PORT_RANGE": 3  # Rango de puertos a probar si el principal está ocupado
}

# =============================================================================
# 7. APARIENCIA Y UI (COLORES, EMOJIS, BARRAS)
# =============================================================================
COLORS = {
    "SUCCESS": 0x57F287, "ERROR": 0xED4245, "INFO": 0x5865F2,
    "WARNING": 0xFEE75C, "XP": 0x9B59B6, "FUN": 0xE91E63,
    "MINECRAFT": 0x2ECC71, "BLUE": 0x3498DB, "GOLD": 0xF1C40F,
    "TEAL": 0x1ABC9C, "ORANGE": 0xE67E22
}

def get_color(key: str) -> int:
    """Convierte un nombre de color a su valor hexadecimal."""
    return COLORS.get(key.upper(), 0xFFFFFF)

UI_CONFIG = {
    "PROGRESS_BAR_FILLED": "▰", "PROGRESS_BAR_EMPTY": "▱",
    "MAX_DESC_LENGTH": 200,  # Límite de caracteres en biografía de perfil
    "PROFILE_BAR_LENGTH": 10,  # Longitud de barra de XP en perfil
    "STATUS_TRUNCATE": 97,  # Truncado para menús de selección de estado
    "MSG_PREVIEW_TRUNCATE": 30,  # Truncado para previsualización de mensajes
    "BAR_LENGTH": 10,  # Longitud de barras de sistema (RAM/CPU)
    "SELECT_DESC_TRUNCATE": 100  # Truncado de descripciones en menús
}

ASSETS = {
    "COINFLIP_HEADS": "https://cdn.discordapp.com/emojis/745519235303735376.gif",
    "COINFLIP_TAILS": "https://cdn.discordapp.com/emojis/745519477935964212.gif"
}

HELP_CONFIG = {
    "EMOJI_MAP": {
        "General": "💡", "Moderacion": "🛡️", "Niveles": "📊", "Diversion": "🎲",
        "Configuracion": "⚙️", "Developer": "💻", "Cumpleanos": "🎂", "Roles": "🎭",
        "Voice": "🎙️", "Perfil": "👤", "Status": "🟢", "Backup": "💾",
        "Usuario": "👤", "Minecraft": "🧱", "Music": "🎵"
    },
    "HOME_EMOJI": "🏠"  # Emoji para volver al inicio del panel de ayuda
}

BOTINFO_CONFIG = {
    "EMOJIS": {"GENERAL": "📊", "SYSTEM": "💻", "MEMORY": "🧠", "CONFIG": "⚙️"},
    "TITLE_EMOJI": "🤖",
    "SELECT_EMOJI": "👇"
}

# =============================================================================
# 8. LOCALIZACIÓN Y CONFIGURACIÓN GENERAL
# =============================================================================
GENERAL_CONFIG = {
    "LARGE_SERVER_THRESHOLD": 1000,  # Servidores con más de X miembros desactivan cálculos pesados
    "DEFAULT_LANG": "es"  # Idioma por defecto del bot
}

DEFAULT_GUILD_CONFIG = {  # Configuración inicial para nuevos servidores
    "language": "es",
    "chaos_enabled": 1,
    "chaos_probability": 0.01
}

BIRTHDAY_CONFIG = {
    "CHECK_INTERVAL_HOURS": 24,  # Frecuencia de revisión de cumpleaños
    "CAKE_ICON": "https://emojigraph.org/media/apple/birthday-cake_1f382.png",  # Icono de felicitación
    "LIST_LIMIT": 10  # Próximos cumpleaños a mostrar en /cumple lista
}

# =============================================================================
# 9. SISTEMA Y RENDIMIENTO (TIMEOUTS, RECONEXIÓN)
# =============================================================================
VOICE_CONFIG = {
    "RECONNECT_BACKOFF": [5, 10, 30]  # Segundos entre intentos de reconexión de voz
}

OPTIMIZATION_CONFIG = {
    "FLUSH_INTERVAL": 60,  # Segundos para vaciar caché de XP
    "CLEANUP_INTERVAL": 6  # Horas para limpieza de memoria RAM
}

TIMEOUT_CONFIG = {
    "HELP": 120,  # Segundos antes de desactivar menú de ayuda
    "BOT_INFO": 120,  # Segundos antes de desactivar panel de info
    "STATUS_DELETE": 60,  # Segundos antes de desactivar menú de borrar estados
    "SERVER_INFO": 120  # Segundos antes de desactivar panel de serverinfo
}

PAGINATION_CONFIG = {
    "TIMEOUT": 120,  # Tiempo de vida de los botones de paginación
    "EMOJIS": {"FIRST": "⏮️", "PREV": "◀️", "NEXT": "▶️", "LAST": "⏭️"}
}

# =============================================================================
# 10. SEGURIDAD Y PERMISOS
# =============================================================================
STATUS_COMMAND_ONLY_OWNER = False  # True: Solo el dueño gestiona estados. False: Admins también.
CHAOS_CONFIG = {
    "DEFAULT_ENABLED": True,  # Estado inicial del sistema Chaos
    "DEFAULT_PROB": 0.01  # Probabilidad por defecto (1%)
}

# =============================================================================
# 11. UTILIDADES Y OTROS
# =============================================================================
MATH_CONFIG = {
    "OP_MAP": {  # Mapeo de palabras clave a símbolos matemáticos
        "sumar": "+", "suma": "+", "add": "+", "+": "+", "mas": "+",
        "restar": "-", "resta": "-", "minus": "-", "-": "-", "menos": "-",
        "multiplicacion": "*", "multiplicar": "*", "por": "*", "*": "*", "x": "*",
        "division": "/", "dividir": "/", "div": "/", "/": "/"
    }
}

DEV_CONFIG = {
    "STATUS_LIMIT": 25,  # Máximo de estados a mostrar en el menú de borrado
    "SERVER_LIST_CHUNK_SIZE": 10,  # Servidores por página en /listservers
    "MEMORY_TOP_LIMIT": 15  # Módulos a mostrar en el top de consumo de RAM
}

PROFILE_CONFIG = {"RESET_KEYWORD": "reset"}  # Palabra para limpiar campos de perfil
ROLES_CONFIG = {"DEFAULT_EMOJI": "✨", "DEFAULT_COLOR": "green"}  # Config de botones de rol