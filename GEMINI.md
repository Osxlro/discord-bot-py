# Instrucciones del Proyecto: Discord Bot Py

Este archivo contiene las directrices, convenciones y detalles arquitectónicos del bot de Discord. Todas las contribuciones, modificaciones o adiciones deben adherirse a estas reglas para mantener la integridad técnica y estructural del proyecto.

## 🏗️ Arquitectura y Estructura (Separación de Responsabilidades)

El proyecto está diseñado de forma modular utilizando un patrón de diseño por capas.

- **`/cogs/` (Capa de Presentación y Enrutamiento):**
  - **`commands/`**: Contiene la definición de comandos tradicionales y Slash Commands. Los cogs aquí solo deben manejar el parsing de argumentos, delegar la ejecución a los servicios y devolver la respuesta al usuario. No incluir consultas SQL ni lógica pesada.
  - **`events/`**: Listeners para los eventos de Discord. **Crítico:** El evento `on_message` debe canalizarse únicamente a través del despachador centralizado `dispatcher.py` para evitar consultas redundantes de base de datos.
  - **`tasks/`**: Tareas en segundo plano (background loops) utilizando `discord.ext.tasks`.
- **`/services/` (Lógica de Negocio y Persistencia):**
  - **`core/`**: Servicios base y compartidos como el motor de base de datos (`database.py`), la fachada de base de datos (`db_service.py`), el sistema de traducción (`lang_service.py`) y la abstracción de caché (`cache_service.py`).
  - **`repositories/`**: Repositorios que encapsulan el acceso SQL directo y las operaciones de caché específicas (`config_repository.py`, `xp_repository.py`, `user_repository.py`).
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

### Capa de Repositorios y Caché Abstracta (services/repositories/ & services/core/cache_service.py)
Para soportar despliegues de gran escala y sharding, el bot cuenta con una arquitectura de persistencia optimizada y desacoplada de `db_service.py`:

1. **Abstracción de Caché (`cache_service.py`)**:
   - Define la interfaz `CacheBackend` con operaciones asíncronas para lectura, escritura, eliminación e invalidación.
   - Implementa `MemoryCacheBackend` (almacenamiento local en RAM) y `RedisCacheBackend` (almacenamiento distribuido rápido en Redis), con un mecanismo automático de fallback a memoria local en caso de error o ausencia de la librería cliente de Redis.

2. **Capa de Repositorios (`services/repositories/`)**:
   - **`ConfigRepository`**: Gestiona las lecturas de configuraciones de servidor mediante caching read-through.
   - **`UserRepository`**: Centraliza las preferencias globales del usuario (cumpleaños, género, monedas) y gestiona la caché de prefijos.
   - **`XpRepository`**: Implementa el almacenamiento diferido (write-behind) para XP/niveles (`_xp_cache`) para agrupar escrituras en disco a través de la tarea de volcado periódico (`flush_xp_cache()`).

3. **Database Core (`database.py`) y Fachada Retrocompatible (`db_service.py`)**:
   - `database.py` expone la conexión física SQLite, el pool en modo WAL y los reintentos asíncronos en caso de bloqueo (`execute_with_retry`).
   - `db_service.py` funciona como una fachada de compatibilidad hacia atrás que redirige todas las llamadas de la aplicación a sus repositorios correspondientes, preservando el 100% de las firmas y evitando actualizar los comandos existentes del bot.

4. **Desacoplamiento de Servicios de Características (e.g., `profile_service.py`)**:
   - Los servicios de características (`services/features/`) deben consumir datos a través de los repositorios de datos correspondientes (como `UserRepository.get_user_data` y `XpRepository.get_user_guild_data`) en lugar de realizar consultas SQL SELECT crudas directamente a la base de datos.

---

## ⚡ Despachador de Eventos Centralizado (Event Dispatcher)

Para optimizar el rendimiento y evitar múltiples accesos concurrentes a la base de datos por cada mensaje recibido, el bot implementa un patrón **Middleware Dispatcher** para el evento `on_message`:

- **Componente Central (`cogs/events/dispatcher.py`)**:
  - Escucha el evento `on_message` global del bot de manera unificada.
  - Realiza validaciones iniciales rápidas (descartar bots, mensajes vacíos, o mensajes fuera de servidores).
  - Consulta la base de datos o caché **una sola vez** para recuperar la configuración del servidor y el idioma localizado.
  - Despacha secuencial o concurrentemente el mensaje, el idioma y la configuración a los métodos lógicos específicos de cada Cog:
    - **XP/Niveles**: `level_events.py` ➔ `process_message_xp(message, lang, config)`
    - **Caos**: `chaos.py` ➔ `process_message_chaos(message, lang, config)`
    - **Menciones**: `mencion.py` ➔ `process_message_mention(message, lang, config)`
- **Regla de Desarrollo**: Ningún Cog de evento individual debe implementar un listener `@commands.Cog.listener("on_message")`. Toda lógica gatillada por mensajes entrantes en servidores debe registrarse y despacharse a través de `dispatcher.py`.

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

## 🎮 Juego del Ahorcado (`/hangman`)

El bot incluye un módulo interactivo para jugar al Ahorcado, accesible mediante comandos híbridos. Sus características y especificaciones técnicas son:

### ⚙️ Especificaciones de Modos y Temporizadores
- **Modo SOLO:** Cuenta con un límite de tiempo global de **3 minutos (180s)**.
- **Modo MULTIPLAYER:** Cuenta con un límite de tiempo global de **5 minutos (300s)** y turnos de 15 segundos por jugador.
- **Control de Palabras Recientes:** Para evitar repetir palabras, `HangmanService` mantiene un historial en memoria de las últimas 30 palabras jugadas **por servidor (guild)**. Al solicitar una nueva palabra, se filtran las coincidencias.
- **Pistas Retardadas (Al restar 1 minuto):**
  - Al iniciar la partida, tanto la pista de definición (`hint`) como la pista de letra inicial (`hint_letter`) se mantienen ocultas. El embed muestra `Oculta hasta el último minuto`.
  - Cuando el tiempo restante del juego es menor o igual a **60 segundos**, se revela la definición y se elige de forma aleatoria una letra no adivinada aún (`HangmanService.get_initial_hint` filtrando letras ya jugadas) para mostrarla en el tablero y notificarla en el canal de chat.

### 🔄 Flujo Consistente de Revanchas
- Al finalizar una partida multijugador, se propone una revancha mediante reacciones al emoji `🔄` con un tiempo de espera de **10 segundos**.
- La revancha se inicia si **al menos uno** de los jugadores originales acepta (reacciona con `🔄`).
- Al iniciar la revancha, se conserva la lista de participantes de la partida previa y se omite por completo la fase de registro emoji `🦅`, acelerando el inicio de las partidas consecutivas.

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

La suite se compone de cinco validadores en el directorio `/tools/`:

1. **Validación de Código (`tools/validate_code.py`)**:
   - Analiza estáticamente la sintaxis de todos los archivos de código del bot y busca nombres de variables indefinidos (`NameError`) en todos los bloques locales y globales.
   - *Ejecución:* `.venv\Scripts\python.exe tools/validate_code.py`

2. **Validación de Comandos y Cogs (`tools/validate_commands.py`)**:
   - Verifica que todos los Cogs tengan la función `setup(bot)` necesaria para su registro (búsqueda recursiva).
   - Audita que todos los comandos híbridos y slash cumplan estrictamente con las reglas de Discord (nombres en minúsculas, sin espacios, de 1 a 32 caracteres, y descripciones válidas menores a 100 caracteres).
   - Valida que todos los parámetros y argumentos de comandos de barra cumplan las reglas estrictas de nomenclatura de Discord (`^[a-z0-9_-]{1,32}$`).
   - Detecta colisiones o nombres duplicados de comandos y subcomandos.
   - *Ejecución:* `.venv\Scripts\python.exe tools/validate_commands.py`

3. **Validación de Internacionalización (`tools/validate_locales.py`)**:
   - Comprueba la sincronía de llaves y paridad de marcadores de formato (como `{user}`, `{level}`) en todos los archivos de traducción (es, en, pt, fr) para prevenir fallos `KeyError` en producción.
   - Analiza mediante AST el código fuente para asegurar que todas las llamadas `get_text` hagan referencia a claves existentes y que los marcadores pasados en la llamada coincidan exactamente con la firma de la traducción.
   - *Ejecución:* `.venv\Scripts\python.exe tools/validate_locales.py`

4. **Validación de Esquema de Base de Datos (`tools/validate_db_schema.py`)**:
   - Comprueba que todas las tablas definidas con `CREATE TABLE` en `init_db()` estén debidamente registradas en la constante `REQUIRED_TABLES` para evitar que la limpieza del bot las remueva.
   - Verifica que cualquier columna nueva agregada a la estructura de las tablas tenga su correspondiente llamada a `_ensure_column()` para garantizar la migración automática y segura en bases de datos existentes.
   - *Ejecución:* `.venv\Scripts\python.exe tools/validate_db_schema.py`

5. **Validación de Normativa de Embeds (`tools/validate_ui_embeds.py`)**:
   - Asegura la consistencia de marca y diseño del bot prohibiendo la instanciación directa de `discord.Embed(...)` en comandos o UI, forzando el uso exclusivo de los helpers en `embed_service.py` (excepto en `profile_ui.py`, `general_ui.py` y `music_ui.py` por razones de color dinámico).
   - *Ejecución:* `.venv\Scripts\python.exe tools/validate_ui_embeds.py`

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

---

## 📋 Protocolo de Desarrollo y Feedback

Para asegurar una comunicación clara y una ejecución ordenada en cada solicitud de cambio, se deben seguir de forma estricta las siguientes pautas:

1. **Análisis y Plan de Implementación Previo:**
   - Antes de iniciar cualquier modificación o adición de código, se debe analizar detalladamente los requerimientos y crear un **Plan de Implementación** (`implementation_plan.md`) para presentárselo al usuario y recibir feedback.
   - No se debe modificar código fuente ni ejecutar comandos de escritura antes de obtener la aprobación explícita del usuario sobre dicho plan.

2. **Ejecución Selectiva de Validadores:**
   - En lugar de ejecutar toda la suite de validadores ante cualquier cambio, se deben ejecutar únicamente los validadores relevantes para el ámbito modificado para optimizar tiempo y recursos (ej: si solo se cambian textos de idioma, ejecutar únicamente `validate_locales.py`; si es un cambio menor de base de datos, `validate_db_schema.py`).
   - Se ejecutará la suite completa al preparar el entregable final o ante cambios de alto impacto que afecten múltiples capas.

3. **Lineamientos Concisos del Walkthrough:**
   - El walkthrough final (`walkthrough.md`) debe seguir un esquema fijo y directo al grano, sin extenderse innecesariamente. Su estructura debe limitarse a:
     - **Cambios Realizados:** Explicación técnica en viñetas breves indicando qué cambió y los archivos afectados.
     - **Pruebas y Resultados:** Lista concreta de los validadores ejecutados y sus resultados de paso.
     - **Verificación Manual:** Pasos breves para probar la funcionalidad en Discord.