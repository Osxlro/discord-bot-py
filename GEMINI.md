# Instrucciones del Proyecto: Discord Bot Py

Este archivo contiene las directrices, convenciones y detalles arquitectónicos del bot de Discord. Todas las contribuciones, modificaciones o adiciones deben adherirse a estas reglas para mantener la integridad técnica y estructural del proyecto.

## 🏗️ Arquitectura y Estructura (Separación de Responsabilidades)

El proyecto está diseñado de forma modular utilizando un patrón de diseño por capas.

- **`/cogs/` (Capa de Presentación y Enrutamiento):**
  - **`commands/`**: Contiene la definición de comandos tradicionales y Slash Commands. Los cogs aquí solo deben manejar el parsing de argumentos, delegar la ejecución a los servicios y devolver la respuesta al usuario. No incluir consultas SQL ni lógica pesada.
  - **`events/`**: Listeners para los eventos de Discord (e.g., `on_message`, `on_member_join`).
  - **`tasks/`**: Tareas en segundo plano (background loops) utilizando `discord.ext.tasks`.
- **`/services/` (Lógica de Negocio y Persistencia):**
  - **`core/`**: Servicios base como la conexión a la base de datos (`db_service.py`) y el sistema multi-idioma (`lang_service.py`).
  - **`features/`**: Lógica detallada por característica (e.g., niveles, economía, música, moderación).
  - **`integrations/`**: Comunicación con servicios de terceros (APIs externas).
  - **`utils/`**: Clases y funciones utilitarias (generación de embeds, paginación, etc.).
- **`/ui/` (Componentes Interactivos):**
  - Contiene todas las definiciones de interfaces enriquecidas (`discord.ui.View`, `discord.ui.Button`, `discord.ui.Modal`).
- **`/config/` (Configuración global):**
  - Contiene los archivos de configuración estática del bot y de localización.

---

## 💾 Esquema de Base de Datos (SQLite)

La persistencia del bot se maneja a través de SQLite3 utilizando `db_service.py`. Esta capa implementa **Write-behind caching** para XP/niveles y **Read-through caching** para configuraciones con el fin de minimizar el I/O en disco.

### Tablas Principales
1. **`users`** (Preferencias globales de usuario):
   - `user_id` (INTEGER PRIMARY KEY)
   - `xp` (INTEGER DEFAULT 0) - XP global
   - `level` (INTEGER DEFAULT 1) - Nivel global
   - `birthday` (TEXT DEFAULT NULL) - Cumpleaños ("DD-MM")
   - `celebrate` (BOOLEAN DEFAULT 1) - Permitir felicitación
   - `custom_prefix` (TEXT DEFAULT NULL) - Prefijo personalizado del usuario
   - `description` (TEXT DEFAULT 'Sin descripción.') - Biografía del usuario
   - `personal_level_msg` (TEXT DEFAULT NULL) - Mensaje personalizado al subir de nivel
   - `personal_birthday_msg` (TEXT DEFAULT NULL) - Mensaje personalizado de cumpleaños

2. **`guild_stats`** (Estadísticas de experiencia por servidor):
   - `guild_id` (INTEGER)
   - `user_id` (INTEGER)
   - `rebirths` (INTEGER DEFAULT 0) - Cantidad de renacimientos realizados
   - `xp` (INTEGER DEFAULT 0) - XP en el servidor
   - `level` (INTEGER DEFAULT 1) - Nivel en el servidor
   - *Llave Primaria:* `(guild_id, user_id)`
   - *Índice:* `idx_ranking` en `(guild_id, rebirths DESC, level DESC, xp DESC)` para optimizar el leaderboard.

3. **`guild_config`** (Configuración específica de cada servidor):
   - `guild_id` (INTEGER PRIMARY KEY)
   - `chaos_enabled` (BOOLEAN DEFAULT 1)
   - `chaos_probability` (REAL DEFAULT 0.01)
   - `welcome_channel_id` (INTEGER DEFAULT 0)
   - `confessions_channel_id` (INTEGER DEFAULT 0)
   - `logs_channel_id` (INTEGER DEFAULT 0)
   - `birthday_channel_id` (INTEGER DEFAULT 0)
   - `autorole_id` (INTEGER DEFAULT 0)
   - `mention_response` (TEXT DEFAULT NULL)
   - `server_level_msg` (TEXT DEFAULT NULL)
   - `server_birthday_msg` (TEXT DEFAULT NULL)
   - `server_kick_msg` (TEXT DEFAULT NULL)
   - `server_ban_msg` (TEXT DEFAULT NULL)
   - `server_goodbye_msg` (TEXT DEFAULT NULL)
   - `minecraft_channel_id` (INTEGER DEFAULT 0)
   - `wordday_channel_id` (INTEGER DEFAULT 0)
   - `wordday_role_id` (INTEGER DEFAULT 0)
   - `language` (TEXT DEFAULT 'es') - Idioma del servidor ("es", "en", "pt", etc.)

4. **`bot_persistence`** (Persistencia binaria genérica para datos varios):
   - `namespace` (TEXT)
   - `key` (TEXT)
   - `data` (BLOB)
   - `created_at` (DATETIME DEFAULT CURRENT_TIMESTAMP)
   - *Llave Primaria:* `(namespace, key)`

5. **`bot_statuses`** (Estados rotativos dinámicos del bot):
   - `id` (INTEGER PRIMARY KEY AUTOINCREMENT)
   - `type` (TEXT DEFAULT 'playing') - Tipo de actividad (playing, watching, listening)
   - `text` (TEXT) - Texto del estado

6. **`warns`** (Registro de advertencias / moderación):
   - `id` (INTEGER PRIMARY KEY AUTOINCREMENT)
   - `guild_id` (INTEGER)
   - `user_id` (INTEGER)
   - `mod_id` (INTEGER) - ID del moderador
   - `reason` (TEXT) - Razón de la advertencia
   - `timestamp` (DATETIME DEFAULT CURRENT_TIMESTAMP)

### Caché y Operaciones en db_service.py
- **`_xp_cache`**: Almacena temporalmente la XP ganada. Se vuelca a la base de datos de manera diferida llamando a `flush_xp_cache()` de forma periódica en un background task para evitar bloqueos por escritura constante en disco.
- **`_config_cache`**: Mantiene en memoria las configuraciones de los servidores para evitar lecturas constantes de disco. Cualquier cambio mediante `update_guild_config()` actualiza tanto la base de datos como esta caché.
- **`_prefix_cache`**: Caché en memoria para las consultas del prefijo personalizado de cada usuario.

---

## 🌐 Internacionalización (i18n) Obligatoria

El bot soporta múltiples idiomas. **Nunca** codificar cadenas de texto estáticas en español o inglés directamente dentro de los comandos.

### Estructura de Traducción
- Los archivos con los textos se encuentran en `/config/lang/` (`es.py`, `en.py`, `pt.py`, `fr.py`). Cada archivo expone un diccionario con las traducciones.
- Las traducciones se registran en [locales.py](file:///c:/Users/PC/Documents/GitHub/discord-bot-py/config/locales.py) mapeando el código de idioma (ej. `es`, `en`) al diccionario.
- El servicio [lang_service.py](file:///c:/Users/PC/Documents/GitHub/discord-bot-py/services/core/lang_service.py) gestiona el idioma.

### Cómo Consumir Textos en el Código
1. Obtén el idioma del servidor usando `lang_service.get_guild_lang(guild_id)`.
2. Recupera la traducción usando `lang_service.get_text("key", lang, **variables)` si necesitas pasar parámetros dinámicos a la cadena (ej. `"{user} ha subido de nivel"`).

```python
# Ejemplo de uso en un comando
lang = await lang_service.get_guild_lang(ctx.guild.id)
mensaje = lang_service.get_text("level_up_msg", lang, user=ctx.author.mention, level=new_level)
```

---

## 🎨 Diseño Visual Constante (Embeds y Colores)

Para mantener la consistencia estética y la identidad del bot, **todas las respuestas visuales** deben estructurarse usando el módulo de utilidad [embed_service.py](file:///c:/Users/PC/Documents/GitHub/discord-bot-py/services/utils/embed_service.py).

### Lineamientos Obligatorios de Diseño de Embeds:
1. **Uso Exclusivo de `embed_service`**:
   - Queda estrictamente prohibido instanciar `discord.Embed` de forma directa en los comandos o componentes de UI, a excepción de las tarjetas de perfil de usuario que necesitan utilizar dinámicamente el color del rol/avatar del usuario.
   - En todos los demás casos, use siempre los helpers correspondientes del servicio.
2. **Formateo de Listas y Datos**:
   - Para mostrar información estructurada, pares clave-valor, estadísticas o configuraciones dentro de la descripción de un embed, se debe utilizar el formato de citas de bloque de Discord:
     `> **Clave:** Valor`
   - Esto unifica la visualización a través de toda la aplicación y mejora drásticamente la legibilidad de la interfaz.
3. **Manejo de Miniaturas (Thumbnails)**:
   - Los embeds de respuestas rápidas y sencillas (`lite=True`) deben omitir thumbnails para mantener la interfaz despejada.
   - Embeds que muestren información compleja o del servidor deben incluir el icono del servidor (`guild.icon.url`) o el avatar del miembro/usuario (`member.display_avatar.url`) como thumbnail.

### Colores de Marca (`settings.COLORS`)
- **Success (Verde):** `0x57F287` - Para confirmaciones y acciones exitosas.
- **Error (Rojo):** `0xED4245` - Para fallas y denegaciones.
- **Info (Azul):** `0x5865F2` - Para listados y textos informativos.
- **Warning (Amarillo):** `0xFEE75C` - Para advertencias y alertas del sistema.
- **XP (Violeta):** `0x9B59B6` - Para tarjetas y mensajes del sistema de niveles.
- **Fun (Rosa):** `0xE91E63` - Comandos divertidos o de entretenimiento.

### Helpers de Embeds a Utilizar
* `embed_service.success(title, description, lite=False, ...)`
* `embed_service.error(title, description, lite=False, ...)`
* `embed_service.info(title, description, lite=False, ...)`
* `embed_service.warning(title, description, lite=False, ...)`
* `embed_service.xp_embed(title, description, ...)`

---

## 🎵 Sistema de Música

- Utiliza `wavelink` (Lavalink) para la reproducción.
- El sistema de música intenta restaurar los reproductores al reiniciarse (`music_service.restore_players`).
- Mantener la eficiencia asegurándose de no dejar reproductores "huérfanos" (memory leaks) si un canal de voz se vacía.

---

## 🔒 Buenas Prácticas y Seguridad

- **Variables de Entorno:** Nunca introducir tokens u otras credenciales en el código. Estas siempre se inyectan a través del archivo `.env`.
  - Variables requeridas/soportadas:
    - `DISCORD_TOKEN`: Token de tu bot de Discord (Requerido).
    - `DATABASE_URL` / `REDIS_URL`: Direcciones para bases de datos externas / Caché (Opcionales).
    - `PRODUCTION`: Flag booleano (`True` o `False`) para habilitar el entorno de producción.
    - `SPOTIFY_CLIENT_ID` / `SPOTIFY_CLIENT_SECRET`: Credenciales para resolver enlaces de Spotify en música.
- **Límites de Uso:** Respetar y no evadir la configuración de *Cooldowns* (Rate Limits) para evitar abusos por parte de los usuarios.
- **Tipado Fuerte (Type Hinting):** Añadir siempre anotaciones de tipos de Python a argumentos y retornos de funciones para mejorar el autocompletado y facilitar la detección de errores lógicos.

---

## 💻 Estructura de un Cog Estándar (Plantilla)

Al crear un nuevo Cog de comandos bajo `cogs/commands/`, se debe seguir este patrón utilizando **comandos híbridos** (funcionan tanto con prefijo tradicional como con Slash Commands) y delegando la lógica a un servicio.

```python
import discord
from discord.ext import commands
from discord import app_commands
from services.core import lang_service
from services.utils import embed_service
# Importar el servicio correspondiente
from services.features import mi_caracteristica_service 

class MiModulo(commands.Cog):
    """Descripción detallada del Cog."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_command(name="mi_comando", description="Descripción del comando visible en Discord.")
    @app_commands.describe(parametro="Explicación del parámetro")
    async def mi_comando(self, ctx: commands.Context, parametro: str):
        """Llama al servicio correspondiente delegando la lógica."""
        # 1. Obtener idioma del servidor
        lang = await lang_service.get_guild_lang(ctx.guild.id if ctx.guild else None)
        
        # 2. Deferir la respuesta si el procesamiento puede demorar más de 3 segundos
        await ctx.defer()
        
        # 3. Delegar lógica pesada o de datos a su servicio en services/features/
        resultado, error = await mi_caracteristica_service.procesar_logica(ctx.author.id, parametro, lang)
        
        if error:
            # Uso del helper de errores de embed_service
            return await ctx.reply(embed=embed_service.error(
                title=lang_service.get_text("title_error", lang), 
                description=error, 
                lite=True
            ))
            
        # 4. Responder con un embed de éxito estándar
        embed = embed_service.success(
            title=lang_service.get_text("title_exito", lang),
            description=lang_service.get_text("mi_mensaje_exito", lang, result=resultado)
        )
        await ctx.reply(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(MiModulo(bot))
```

---

## 🚨 Protocolo ante Bugs, Errores y Fallos Críticos

Para garantizar la estabilidad y fácil mantenimiento del bot en entornos de producción, se debe seguir este protocolo ante incidentes:

1. **Monitoreo y Diagnóstico con Logs:**
   - Ubicación del log rotativo: `data/discord.log` (Rotación automática: 5 archivos de hasta 5MB).
   - Siempre registrar excepciones usando `logger.exception("Mensaje del error")` para capturar la traza completa (stack trace).

2. **Suite de Autodiagnóstico Activo (`health_check.py`):**
   - El bot ejecuta una prueba automática en segundo plano cada 30 minutos (`cogs/tasks/health_check.py`).
   - Comprueba la integridad física de la base de datos (PRAGMA check), tamaño del disco, estado de los nodos Lavalink, credenciales de Spotify, paridad de las claves i18n entre idiomas, y uso de CPU/RAM.
   - Si se detecta un fallo, el bot enviará un mensaje directo (DM) automático con la alerta al dueño de la aplicación.

3. **Manejo de Excepciones en Comandos:**
   - Centralizado en `cogs/events/error_handler.py`. Evitar bloques `try/except` genéricos que silencien errores en la capa del comando; permitir que escalen al manejador global.
   - Enviar siempre respuestas visuales controladas usando `embed_service.error(...)` e internacionalizadas.

4. **Respaldo y Recuperación ante Pérdida de Datos:**
   - La tarea `cogs/tasks/backup.py` realiza un volcado de XP en memoria a disco cada 5 minutos (`flush_xp_cache()`) y genera un backup completo de la base de datos SQLite cada 12 horas.
   - El backup se envía directamente al DM del dueño del bot. Solo se mantienen los últimos 3 backups en el historial para evitar saturar el almacenamiento.
   - Para restaurar en caso de corrupción: Detener el bot, descargar el último archivo sqlite3 del DM, renombrarlo a `database.sqlite3` en `/data/`, y reiniciar.

5. **Garantía de Tiempo de Actividad (Resiliency):**
   - En producción, ejecutar siempre el bot bajo un gestor de procesos (como `PM2` o un servicio de `systemd`) que lo reinicie automáticamente en caso de detención inesperada o caída fatal del proceso de Python.