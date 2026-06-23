import os
from dotenv import load_dotenv

# Cargar variables de entorno desde el archivo .env
load_dotenv()

# =============================================================================
# 1. NÚCLEO Y ENTORNO (CORE & ENVIRONMENT)
# =============================================================================
# Configuración fundamental para la conexión y el entorno de ejecución del bot.

TOKEN = os.getenv("DISCORD_TOKEN")  # Token de autenticación del bot de Discord
DATABASE_URL = os.getenv("DATABASE_URL")  # Conexión opcional a base de datos externa (PostgreSQL/MySQL)
REDIS_URL = os.getenv("REDIS_URL")  # URL de caché Redis (opcional)
IS_PRODUCTION = os.getenv("PRODUCTION", "True") == "True"  # Bandera para identificar entorno de producción
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # Directorio raíz del proyecto
LOG_FILE = os.path.join(BASE_DIR, "data", "discord.log")  # Ruta para el guardado de logs rotativos


# =============================================================================
# 2. IDENTIDAD Y CONFIGURACIÓN BÁSICA DEL BOT
# =============================================================================
# Ajustes que definen el comportamiento general e identidad inicial de la aplicación.

CONFIG = {
    "bot_config": {
        "prefix": "=",  # Prefijo por defecto para comandos de texto tradicionales (legacy)
        "version": "1.5",  # Versión del software del bot
        "description": "Oscurin Inc",  # Descripción corta de la aplicación
        "presence_asset": "seor"  # Nombre de la imagen del estado personalizado (Rich Presence)
    },
    "moderation_config": {
        "max_clear_msg": 50,  # Máximo de mensajes permitidos para purgar con /clear
        "delete_after": 5,  # Segundos para auto-eliminar embeds efímeros/confirmaciones
        "timeout_limit": 2419200,  # Tiempo máximo de aislamiento (28 días en segundos)
        "warns_page_size": 5  # Cantidad de advertencias por página en el comando /warns
    }
}

DEFAULT_STATUSES = [  # Estados por defecto (actividades) a rotar si la base de datos está vacía
    {"type": "playing", "text": "Visual Studio Code"},
    {"type": "watching", "text": "a los usuarios"},
    {"type": "listening", "text": "tus comandos /"}
]

# Caché en memoria para almacenar la URL del avatar del bot y evitar llamadas recurrentes a la API
_BOT_ICON_URL = None

def set_bot_icon(url: str):
    """Establece globalmente el enlace al avatar del bot."""
    global _BOT_ICON_URL
    _BOT_ICON_URL = url

def get_bot_icon() -> str:
    """Retorna la URL guardada del avatar del bot o un string vacío."""
    return _BOT_ICON_URL or ""


# =============================================================================
# 3. INTERFAZ DE USUARIO Y TIEMPO DE EXPIRACIÓN (TIMEOUTS & UI)
# =============================================================================
# Ajustes generales para el renderizado visual de paneles interactivos.

# [MEJORA GENERALIZADA] - Tiempo de vida global (en segundos) para la inactividad en componentes interactivos
# (botones, selectores y menús desplegables: ayuda, perfil, serverinfo, borrar estados, etc.)
GLOBAL_TIMEOUT = 120  

TIMEOUT_CONFIG = {
    "HELP": GLOBAL_TIMEOUT,          # Segundos antes de desactivar menú de ayuda
    "BOT_INFO": GLOBAL_TIMEOUT,      # Segundos antes de desactivar panel de información técnica
    "STATUS_DELETE": GLOBAL_TIMEOUT,  # Segundos antes de desactivar selección para borrar estados
    "SERVER_INFO": GLOBAL_TIMEOUT    # Segundos antes de desactivar panel de serverinfo
}

PAGINATION_CONFIG = {
    "TIMEOUT": GLOBAL_TIMEOUT,  # Tiempo de vida de los botones en embeds paginados
    "EMOJIS": {"FIRST": "⏮️", "PREV": "◀️", "NEXT": "▶️", "LAST": "⏭️"}
}

UI_CONFIG = {
    "PROGRESS_BAR_FILLED": "▰",  # Símbolo para barras de progreso (completado)
    "PROGRESS_BAR_EMPTY": "▱",   # Símbolo para barras de progreso (restante)
    "MAX_DESC_LENGTH": 200,      # Límite de caracteres en biografías de tarjetas de perfil
    "PROFILE_BAR_LENGTH": 10,    # Cantidad de segmentos en la barra de XP del perfil
    "STATUS_TRUNCATE": 97,        # Truncado de estados en menús desplegables
    "MSG_PREVIEW_TRUNCATE": 30,  # Truncado para avances de mensajes largos
    "BAR_LENGTH": 10,            # Bloques para barras de estado del sistema (CPU/RAM)
    "SELECT_DESC_TRUNCATE": 100  # Truncado para descripciones en menús Select
}

HELP_CONFIG = {
    "EMOJI_MAP": {  # Asignación de emojis estéticos para cada módulo en /help
        "General": "💡", "Moderacion": "🛡️", "Niveles": "📊", "Diversion": "🎲",
        "Configuracion": "⚙️", "Developer": "💻", "Cumpleanos": "🎂", "Roles": "🎭",
        "Voice": "🎙️", "Perfil": "👤", "Status": "🟢", "Backup": "💾",
        "Usuario": "👤", "Music": "🎵" # "Minecraft": "🧱" (Archivado)
    },
    "HOME_EMOJI": "🏠"  # Emoji para el botón de regreso al panel principal de ayuda
}

BOTINFO_CONFIG = {
    "EMOJIS": {"GENERAL": "📊", "SYSTEM": "💻", "MEMORY": "🧠", "CONFIG": "⚙️"},
    "TITLE_EMOJI": "🤖",
    "SELECT_EMOJI": "👇"
}

ASSETS = {
    "COINFLIP_HEADS": "https://cdn.discordapp.com/emojis/745519235303735376.gif",
    "COINFLIP_TAILS": "https://cdn.discordapp.com/emojis/745519477935964212.gif"
}

COLORS = {  # Paleta de colores oficiales de marca del bot
    "SUCCESS": 0x57F287, "ERROR": 0xED4245, "INFO": 0x5865F2,
    "WARNING": 0xFEE75C, "XP": 0x9B59B6, "FUN": 0xE91E63,
    # "MINECRAFT": 0x2ECC71, (Archivado)
    "BLUE": 0x3498DB, "GOLD": 0xF1C40F,
    "TEAL": 0x1ABC9C, "ORANGE": 0xE67E22
}

def get_color(key: str) -> int:
    """Devuelve el valor hexadecimal del color o blanco como fallback."""
    return COLORS.get(key.upper(), 0xFFFFFF)

DIVERSION_CONFIG = {
    "KAOMOJIS": ["(◕‿◕)", "(´• ω •`)", "(つ✧ω✧)つ", "(o^▽^o)", "(≧◡≦)", "(⌒‿⌒)", "(^人^)", "(✿◠‿◠)", "(｀▽´)", "(◕‿◕✿)", "(*^ω^*)"],
    "HANGMAN_EMOJIS": {
        "REGISTER": "🦅",
        "REMATCH": "🔄"
    }
}


# =============================================================================
# 4. SISTEMA DE MÚSICA (LAVALINK & SOUND CLOUD/SPOTIFY)
# =============================================================================
# Ajustes del reproductor musical y la conexión con nodos de Lavalink.

LAVALINK_CONFIG = {
    "NODES": [  # Lista de servidores Lavalink con redundancia de fallos
        {"HOST": "lavalink.jirayu.net", "PORT": 13592, "PASSWORD": "youshallnotpass", "SECURE": False, "IDENTIFIER": "Jirayu-NonSSL"},
        {"HOST": "lavalinkv4.serenetia.com", "PORT": 80, "PASSWORD": "https://dsc.gg/ajidevserver", "SECURE": False, "IDENTIFIER": "Serenetia-NonSSL"},
        {"HOST": "lavalinkv4.serenetia.com", "PORT": 443, "PASSWORD": "https://dsc.gg/ajidevserver", "SECURE": True, "IDENTIFIER": "Serenetia-SSL"},
        {"HOST": "lavalink.jirayu.net", "PORT": 443, "PASSWORD": "youshallnotpass", "SECURE": True, "IDENTIFIER": "Jirayu-SSL"},
    ],
    "DEFAULT_VOLUME": 50,  # Volumen base inicial
    "SEARCH_PROVIDER": "spsearch",  # Proveedor de búsqueda ('spsearch' para Spotify, 'ytsearch' para YouTube)
    "INACTIVITY_TIMEOUT": 300,  # Segundos antes de apagar el reproductor si el canal de voz se vacía
    "CACHE_CAPACITY": 100,  # Capacidad máxima del caché interno de canciones en Wavelink
    "SPOTIFY": {  # Credenciales de API de Spotify
        "CLIENT_ID": os.getenv("SPOTIFY_CLIENT_ID", ""),
        "CLIENT_SECRET": os.getenv("SPOTIFY_CLIENT_SECRET", "")
    }
}

MUSIC_CONFIG = {
    "QUEUE_PAGE_SIZE": 10,  # Canciones mostradas por página en el panel /queue
    "AUTOCOMPLETE_LIMIT": 10,  # Cantidad máxima de autocompletado en el comando /play
    "PROGRESS_BAR_LENGTH": 15,  # Segmentos de la barra de progreso de reproducción
    "STREAM_BAR_LENGTH": 15,  # Segmentos de la barra para directos (livestreams)
    "CROSSFADE_DURATION": 3000,  # Milisegundos de crossfade al pasar de pista (si el reproductor lo soporta)
    "VOLUME_STEP": 10,  # Nivel que sube/baja el volumen al interactuar con botones
    "AUTOCOMPLETE_TITLE_LIMIT": 65,  # Límite de caracteres en títulos sugeridos
    "AUTOCOMPLETE_AUTHOR_LIMIT": 15,  # Límite de caracteres de autores sugeridos
    "FADE_IN_STEPS": 15,  # Pasos intermedios para animaciones de desvanecimiento
    "LOOP_EMOJIS": {"TRACK": "🔂", "QUEUE": "🔁", "OFF": "🔁"},
    "BUTTON_EMOJIS": {
        "PREVIOUS": "⏮️", "PAUSE_RESUME": "⏯️", "SKIP": "⏭️", "QUEUE": "📜", "STOP": "⏹️", "SHUFFLE": "🔀",
        "AUTOPLAY": "♾️", "VOL_DOWN": "🔉", "VOL_UP": "🔊", "LYRICS": "📝"
    },
    "SOURCE_EMOJIS": {
        "youtube": "🔴", "spotify": "🟢", "soundcloud": "🟠", "unknown": "🎵"
    },
    "PROGRESS_BAR_CHAR": "▬",
    "PROGRESS_BAR_POINTER": "🔘",
    "VOLUME_TOLERANCE": 1,  # Rango de detección de cambio manual de volumen
    "CONTROLS_TIMEOUT": None  # Tiempo de vida de botones del reproductor (None = Infinito)
}

ALGORITHM_CONFIG = {  # Ajustes de recomendación y autoplay inteligente
    "HISTORY_LIMIT": 30,  # Últimas canciones a omitir para no repetirlas en Autoplay
    "SIMILARITY_THRESHOLD": 0.85,  # Límite porcentual para descartar temas duplicados
    "DEFAULT_METADATA": "Unknown",  # Metadata por defecto ante nulos
    "STYLE_KEYWORDS": [
        "nightcore", "daycore", "lo-fi", "lofi", "remix", "acoustic", 
        "live", "cover", "instrumental", "slowed", "reverb", "bassboost",
        "speed up", "8d", "mashup"
    ],
    "MOODS": {  # Perfiles de energía para reproducción automática según la hora del día
        "late_night": {"genres": ["indie", "acoustic", "lofi", "jazz"], "energy_range": (0.0, 0.4)},
        "morning": {"genres": ["pop", "indie", "acoustic"], "energy_range": (0.3, 0.6)},
        "day": {"genres": ["pop", "rock", "hiphop", "reggaeton"], "energy_range": (0.6, 1.0)},
        "evening": {"genres": ["rock", "edm", "hiphop", "metal"], "energy_range": (0.5, 0.9)}
    },
    "GENRE_MAP": {  # Listas de artistas por género musical para alimentar el motor de recomendaciones
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
# 5. ECONOMÍA, EXPERIENCIA (XP) Y NIVELES
# =============================================================================
# Fórmulas y ajustes del sistema gamificado del bot.

XP_CONFIG = {
    "MIN_XP": 15,  # XP mínima generada por mensaje
    "MAX_XP": 25,  # XP máxima generada por mensaje
    "COOLDOWN": 60.0,  # Cooldown en segundos antes de volver a ganar XP por chat
    "VOICE_AMOUNT": 15,  # XP otorgada por intervalo en canal de voz
    "VOICE_INTERVAL": 300  # Intervalo de recuento en canal de voz (5 minutos en segundos)
}

LEVELS_CONFIG = {
    "LEADERBOARD_LIMIT": 50,  # Límite del ranking de usuarios
    "XP_MULTIPLIER": 100,  # Multiplicador del nivel para calcular XP necesaria
    "XP_EXPONENT": 1.2,  # Exponente matemático de curva de dificultad
    "REBIRTH_LEVEL": 100,  # Nivel mínimo requerido para poder renacer (Hacer Rebirth)
    "MEDALS": ["🥇", "🥈", "🥉"],  # Emojis decorativos para el top del ranking
    "LEADERBOARD_CHUNK_SIZE": 10,  # Miembros listados por página en /levels
    "REBIRTH_COST": 100,  # Coste en monedas por cada rebirth ejecutado
    "COINS_PER_LEVEL": (5, 10)  # Rango de monedas ganadas al subir de nivel (mínimo, máximo)
}


# =============================================================================
# 6. BASE DE DATOS Y RESPALDOS (DATABASE & BACKUPS)
# =============================================================================
# Ajustes de almacenamiento e intervalos para persistencia SQLite.

DB_CONFIG = {
    "DIR_NAME": "data",  # Directorio para almacenar la base de datos
    "FILE_NAME": "database.sqlite3",  # Nombre físico del archivo
    "TEMP_BACKUP_NAME": "temp_backup.sqlite3",  # Archivo temporal para generación de backups
    "RETRIES": 3,  # Cantidad de reintentos en bloqueos por concurrencia
    "RETRY_DELAY": 0.1  # Segundos de delay entre reintentos
}

BACKUP_CONFIG = {
    "HISTORY_LIMIT": 50,  # Mensajes analizados al buscar respaldos antiguos
    "MAX_BACKUPS_TO_KEEP": 3,  # Máximo de copias de seguridad a almacenar en el DM del dueño
    "COOLDOWN_SECONDS": 84600,  # Segundos mínimos entre ejecuciones de copias
    "DM_HISTORY_LIMIT": 20,  # Límite de limpieza de mensajes en el chat del dueño
    "KEYWORD": "Backup",  # Palabra clave para buscar mensajes del sistema de backup
    "INTERVAL_HOURS": 12,  # Frecuencia en horas para respaldar
    "XP_FLUSH_MINUTES": 5  # Minutos de intervalo para bajar el XP en memoria a la DB
}

SEND_BACKUP_TO_OWNER = True  # Bandera para habilitar o desactivar el envío de backups por mensaje directo


# =============================================================================
# 7. INTEGRACIONES EXTERNAS (MINECRAFT BRIDGE) [ARCHIVADO]
# =============================================================================
# Servidor web local Flask/Sanic para comunicación bidireccional con plugins Spigot/Paper.
# MINECRAFT_CONFIG = {
#     "ENABLED": False,  # Activar el bridge de Minecraft
#     "PORT": 5058,  # Puerto de escucha del socket/servidor
#     "DEFAULT_NAME": "Steve",  # Fallback de nombre si falla la obtención del usuario
#     "TOKEN": "CAMBIAME_POR_UN_TOKEN_SEGURO",  # Token de seguridad compartido con el plugin
#     "MAX_PAYLOAD_SIZE": 51200,  # Tamaño máximo de carga (50KB)
#     "HOST": "0.0.0.0",  # Dirección del servidor web
#     "MAX_QUEUE_SIZE": 50,  # Límite de mensajes pendientes de sincronizar
#     "PORT_RANGE": 3  # Puertos secundarios a probar si el principal está en uso
# }


# =============================================================================
# 8. LOCALIZACIÓN E IDIOMAS (I18N)
# =============================================================================
# Ajustes multi-lenguaje.

GENERAL_CONFIG = {
    "LARGE_SERVER_THRESHOLD": 1000,  # A partir de este número de usuarios se limitan escaneos masivos
    "DEFAULT_LANG": "es"  # Idioma por defecto del bot
}

DEFAULT_GUILD_CONFIG = {  # Configuración inicial para nuevos servidores agregados
    "language": "es",
    "chaos_enabled": 1,
    "chaos_probability": 0.01
}


# =============================================================================
# 9. SISTEMAS ESPECIALES Y CONFIGURACIÓN DE COGS (CHAOS, BIRTHDAYS, ETC.)
# =============================================================================
# Parámetros para cogs especiales de administración y diversión.

CHAOS_CONFIG = {
    "DEFAULT_ENABLED": True,  # Estado activo por defecto para Chaos
    "DEFAULT_PROB": 0.01  # Probabilidad inicial del 1%
}

BIRTHDAY_CONFIG = {
    "CHECK_INTERVAL_HOURS": 24,  # Intervalo de escaneo diario de cumpleaños
    "CAKE_ICON": "https://emojigraph.org/media/apple/birthday-cake_1f382.png",  # Banner del embed de cumpleaños
    "LIST_LIMIT": 10  # Cantidad de cumpleaños listados en /cumple lista
}

VOICE_CONFIG = {
    "RECONNECT_BACKOFF": [5, 10, 30]  # Tiempos de espera al intentar reconectar canales de voz
}

OPTIMIZATION_CONFIG = {
    "FLUSH_INTERVAL": 60,  # Segundos para purgar caché de niveles
    "CLEANUP_INTERVAL": 6  # Frecuencia en horas para liberar variables de memoria RAM no usadas
}


# =============================================================================
# 10. SEGURIDAD, PERMISOS Y DESARROLLADOR (DEV & COMMANDS)
# =============================================================================
# Ajustes reservados para el administrador/owner y configuración de comandos.

STATUS_COMMAND_ONLY_OWNER = False  # True: Solo el dueño gestiona estados. False: Admins de guild también.

MATH_CONFIG = {
    "OP_MAP": {  # Diccionario mapeador para calculadora en lenguaje natural (/calc)
        "sumar": "+", "suma": "+", "add": "+", "+": "+", "mas": "+",
        "restar": "-", "resta": "-", "minus": "-", "-": "-", "menos": "-",
        "multiplicacion": "*", "multiplicar": "*", "por": "*", "*": "*", "x": "*",
        "division": "/", "dividir": "/", "div": "/", "/": "/"
    }
}

DEV_CONFIG = {
    "STATUS_LIMIT": 25,  # Máximo de estados a renderizar en /developer status list
    "SERVER_LIST_CHUNK_SIZE": 10,  # Servidores por página en /listservers
    "MEMORY_TOP_LIMIT": 15  # Cantidad de módulos mostrados en el top de consumo de memoria RAM
}

PROFILE_CONFIG = {
    "RESET_KEYWORD": "reset"  # Palabra clave utilizada para limpiar campos del perfil
}

ROLES_CONFIG = {
    "DEFAULT_EMOJI": "✨",  # Emoji para botones de rol del bot
    "DEFAULT_COLOR": "green"  # Estilo de color inicial de botones de rol
}

TRIVIA_CONFIG = {
    "REWARDS": {
        "easy": (5, 10),      # Monedas mínima y máxima ganadas en preguntas fáciles
        "medium": (10, 20),   # Monedas mínima y máxima ganadas en preguntas medias
        "hard": (20, 30)      # Monedas mínima y máxima ganadas en preguntas difíciles
    }
}