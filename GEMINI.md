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
   - `birthday` (TEXT DEFAULT NULL) - Cumpleaños ("DD-MM")
   - `celebrate` (BOOLEAN DEFAULT 1) - Permitir felicitación
   - `custom_prefix` (TEXT DEFAULT NULL) - Prefijo personalizado del usuario
   - `description` (TEXT DEFAULT 'Sin descripción.') - Biografía del usuario
   - `personal_level_msg` (TEXT DEFAULT NULL) - Mensaje personalizado al subir de nivel
   - `personal_birthday_msg` (TEXT DEFAULT NULL) - Mensaje personalizado de cumpleaños
   - `coins` (INTEGER DEFAULT 0) - Monedas globales del usuario (sistema de economía)

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
   - Queda estrictamente prohibido instanciar `discord.Embed` de forma directa en los comandos o componentes de UI, a excepción de `profile_ui.py` (tarjetas de perfil con color de rol/avatar dinámico), `general_ui.py` (tarjeta de /serverinfo con color del bot dinámico) y `music_ui.py` (reproductor de música con color de fuente de audio dinámico).
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

## 🖼️ Integración de NekosAPI (Búsqueda de Imágenes Anime)

Para la obtención de imágenes y GIFs de anime, el bot se integra con **NekosAPI v4**. Las directrices, estructura y consideraciones técnicas son las siguientes:

### Detalles del API:
* **Base URL:** `https://api.nekosapi.com/v4`
* **Servicio Desacoplado:** Toda la lógica de consulta y conexión HTTP debe residir de manera independiente en el servicio [nekos_api_service.py](file:///c:/Users/PC/Documents/GitHub/discord-bot-py/services/integrations/nekos_api_service.py).
* **Parámetros de Entrada Clave:**
  - `rating`: Control de contenido (`safe`, `suggestive`, `borderline`, `explicit`). Por defecto y seguridad del servidor, se debe usar siempre `safe`.
  - `tags`: Filtro opcional por etiquetas (cadena separada por comas).

### Estructura de Respuesta JSON (Schema):
Las consultas a `/images/random` o `/images/{id}` retornan un objeto JSON (o lista de objetos en el caso de random) con los siguientes campos útiles:
* `id` (int): Identificador único de la imagen.
* `url` (str): Enlace directo de la imagen/gif (comúnmente formato `.webp`).
* `rating` (str): Nivel de seguridad de la imagen.
* `artist_name` (str o null): Nombre del artista de la ilustración.
* `tags` (list de str): Etiquetas/categorías descriptivas (ej: `girl`, `blue_hair`).
* `source_url` (str o null): Enlace original de la ilustración (ej: Pixiv).

### Reglas de Diseño de Embeds Anime:
1. **Omitir Atributos Nulos:** Si `artist_name`, `source_url` o `tags` son nulos o están vacíos en el JSON, no se deben renderizar en el embed (skipear).
2. **Presentación Visual:** Mostrar la ilustración usando el método `image` del embed (no thumbnail) para que se aprecie a pantalla completa dentro del canal.

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

## ⚙️ Directrices para Comandos de Configuración (`/setup`)

Para evitar la saturación de subcomandos individuales en la interfaz de Discord y simplificar el mantenimiento, la configuración del bot se centraliza en comandos modulares organizados por tipo de recurso (`channel`, `role`, `message`, `system`, `lang`, `streamalert`).

### Reglas Obligatorias de Diseño para Setups:
1. **Unificación por Tipo de Recurso:** 
   - Queda prohibido crear subcomandos específicos para cada parámetro individual (por ejemplo: `/setup welcome_channel` o `/setup logs_channel`). En su lugar, agrégalos como opciones dentro del comando modular correspondiente (ej: `/setup channel tipo:[opciones]`).
2. **Validación Mediante Literals:**
   - Usa `typing.Literal` para restringir los valores permitidos del parámetro `tipo` (ej. `Literal["welcome", "confess", "logs"]`). Esto genera menús desplegables interactivos en Discord y previene entradas inválidas.
3. **Mapeos Clave-Valor Internos:**
   - Utiliza diccionarios internos (`col_map` y `label_map`) en el comando del Cog para mapear la selección del usuario a la columna correspondiente en SQLite y a su clave de traducción localized.
4. **Desactivación de Parámetros:**
   - Permite la desactivación del parámetro pasando un valor por defecto (ej. omitir el canal/rol se traduce a `0` para indicar desactivado, y omitir un mensaje personalizado se evalúa a `None` o `"reset"`).
5. **Uso Exclusivo de `setup_service`:**
   - Toda actualización en la configuración del servidor debe delegarse al servicio [setup_service.py](file:///c:/Users/PC/Documents/GitHub/discord-bot-py/services/features/setup_service.py), el cual actualiza tanto la base de datos SQLite como la caché en memoria (`_config_cache`).

---

### Ejemplo Base / Plantilla de un Comando `/setup` Modular

Al agregar nuevos parámetros de configuración al bot, se debe seguir este patrón dentro de [configuracion.py](file:///c:/Users/PC/Documents/GitHub/discord-bot-py/cogs/commands/configuracion.py):

```python
import discord
from discord import app_commands
from discord.ext import commands
from typing import Literal
from services.core import lang_service
from services.features import setup_service
from services.utils import embed_service

class MiConfiguracion(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # Helper interno para aplicar cambios y responder de forma estandarizada
    async def _apply_setup(self, ctx: commands.Context, updates: dict, label: str, value_display: str):
        await ctx.defer(ephemeral=True)
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        embed = await setup_service.handle_setup_update(ctx.guild.id, updates, lang, label, value_display)
        await ctx.send(embed=embed, ephemeral=True)

    @commands.hybrid_group(name="setup", description="Panel de configuración del servidor.")
    @commands.has_permissions(administrator=True)
    async def setup(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    # Ejemplo de configuración de canales
    @setup.command(name="channel", description="Configura los canales de los distintos sistemas del bot.")
    @app_commands.describe(
        tipo="El sistema a configurar",
        canal="Canal de Discord a asociar (deja vacío para desactivar)"
    )
    async def setup_channel(self, ctx: commands.Context, tipo: Literal["welcome", "logs", "ejemplo_nuevo"], canal: discord.TextChannel = None):
        """Asigna o desactiva el canal para un sistema en específico."""
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        
        # 1. Mapear selección a la columna en base de datos
        col_map = {
            "welcome": "welcome_channel_id",
            "logs": "logs_channel_id",
            "ejemplo_nuevo": "nuevo_channel_id"  # Columna en la DB
        }
        
        # 2. Mapear selección a la clave del archivo lang/
        label_map = {
            "welcome": "setup_label_welcome",
            "logs": "setup_label_logs",
            "ejemplo_nuevo": "setup_label_nuevo"  # Clave de traducción
        }
        
        col = col_map[tipo]
        label = lang_service.get_text(label_map[tipo], lang)
        
        val = canal.id if canal else 0
        display = canal.mention if canal else lang_service.get_text("setup_disabled", lang)
        
        # 3. Guardar cambios usando setup_service
        await self._apply_setup(ctx, {col: val}, label, display)
```

---

## 🧪 Protocolo de Pruebas y Validaciones Obligatorias

Para prevenir errores de sintaxis, variables indefinidas o discrepancias de internacionalización, es **obligatorio** ejecutar la suite de validación estática local después de realizar cualquier cambio en el código, comandos o traducciones, y antes de hacer commits o desplegar en producción.

La suite se compone de cinco validadores en el directorio `/validators/`:

1. **Validación de Código (`validators/validate_code.py`)**:
   - Analiza estáticamente la sintaxis de todos los archivos de código del bot y busca nombres de variables indefinidos (`NameError`) en todos los bloques locales y globales.
   - *Ejecución:* `.venv\Scripts\python.exe validators/validate_code.py`

2. **Validación de Comandos y Cogs (`validators/validate_commands.py`)**:
   - Verifica que todos los Cogs tengan la función `setup(bot)` necesaria para su registro (búsqueda recursiva).
   - Audita que todos los comandos híbridos y slash cumplan estrictamente con las reglas de Discord (nombres en minúsculas, sin espacios, de 1 a 32 caracteres, y descripciones válidas menores a 100 caracteres).
   - Valida que todos los parámetros y argumentos de comandos de barra cumplan las reglas estrictas de nomenclatura de Discord (`^[a-z0-9_-]{1,32}$`).
   - Detecta colisiones o nombres duplicados de comandos y subcomandos.
   - *Ejecución:* `.venv\Scripts\python.exe validators/validate_commands.py`

3. **Validación de Internacionalización (`validators/validate_locales.py`)**:
   - Comprueba la sincronía de llaves y paridad de marcadores de formato (como `{user}`, `{level}`) en todos los archivos de traducción (es, en, pt, fr) para prevenir fallos `KeyError` en producción.
   - Analiza mediante AST el código fuente para asegurar que todas las llamadas `get_text` hagan referencia a claves existentes y que los marcadores pasados en la llamada coincidan exactamente con la firma de la traducción.
   - *Ejecución:* `.venv\Scripts\python.exe validators/validate_locales.py`

4. **Validación de Esquema de Base de Datos (`validators/validate_db_schema.py`)**:
   - Comprueba que todas las tablas definidas con `CREATE TABLE` en `init_db()` estén debidamente registradas en la constante `REQUIRED_TABLES` para evitar que la limpieza del bot las remueva.
   - Verifica que cualquier columna nueva agregada a la estructura de las tablas tenga su correspondiente llamada a `_ensure_column()` para garantizar la migración automática y segura en bases de datos existentes.
   - *Ejecución:* `.venv\Scripts\python.exe validators/validate_db_schema.py`

5. **Validación de Normativa de Embeds (`validators/validate_ui_embeds.py`)**:
   - Asegura la consistencia de marca y diseño del bot prohibiendo la instanciación directa de `discord.Embed(...)` en comandos o UI, forzando el uso exclusivo de los helpers en `embed_service.py` (excepto en `profile_ui.py`, `general_ui.py` y `music_ui.py` por razones de color dinámico).
   - *Ejecución:* `.venv\Scripts\python.exe validators/validate_ui_embeds.py`

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