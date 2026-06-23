# 🤖 Discord Bot Py

> Un bot de Discord modular, multilingüe y de alto rendimiento diseñado para potenciar tu comunidad de forma intuitiva, fluida y con un consumo de recursos ultra bajo.

---

## 🌟 ¿Qué es Discord Bot Py?

**Discord Bot Py** es tu aliado ideal para gestionar, entretener y moderar tu servidor de Discord. Con soporte para múltiples idiomas nativos (Español, Inglés, Portugués y Francés) y una interfaz rica en botones y paneles interactivos, ofrece una experiencia de usuario moderna y profesional.

---

## ⚡ Características Destacadas

### 🎵 Sistema de Música Premium
* **Audio de Alta Fidelidad:** Reproducción fluida y sin lag a través de Lavalink.
* **Paneles Interactivos:** Controla la música de forma visual con botones para pausar, saltar, reproducir, ajustar volumen e interactuar con la letra de la canción.
* **Autoplay inteligente:** ¿Terminó la cola de reproducción? El bot recomendará y reproducirá automáticamente canciones similares según el ambiente actual.
* **Autocompletado Rápido:** Encuentra tus temas favoritos al instante mientras escribes `/play`.

### 📈 Niveles, Experiencia y Economía
* **Progresión Dinámica:** Gana puntos de experiencia (XP) de forma fluida chateando en canales de texto o conversando en canales de voz.
* **Renacimientos (Rebirths):** Alcanza el nivel máximo y renace para lucir medallas de prestigio y ganar monedas en el ranking.
* **Tablas de Clasificación:** Consulta los rankings del servidor con menús paginados y medallas interactivas.

### 🛡️ Moderación y Administración Completa
* **Servidor Bajo Control:** Comandos rápidos de expulsión (`kick`), baneo (`ban`), purga de mensajes (`clear`) y aislamiento (`timeout`).
* **Auto-Roles al Instante:** Configura roles automáticos para dar la bienvenida a nuevos miembros tan pronto como entren.
* **Canales de Logs:** Registros detallados para que los administradores no se pierdan ningún evento crucial del servidor.

### ⚙️ Configuración y Utilidades Avanzadas
* **Cumpleaños Automáticos:** Deja que el bot felicite a los miembros en su día especial con embeds personalizados.
* **Frase del Día:** Publica una cita motivacional o inspiradora cada mañana en el canal asignado.
* **Confesiones Anónimas:** Un canal seguro para que los usuarios envíen confesiones anónimas con total privacidad.

---

## 🎮 Comandos Populares y Uso

El bot soporta tanto **Slash Commands (Comandos de Barra `/`)** como **comandos clásicos con prefijo (`=`)**. 

* `/help` - Abre el panel interactivo de ayuda categorizado con comandos cliqueables.
* `/serverinfo` - Muestra información detallada del servidor en pestañas organizadas (General, Estadísticas y Configuración).
* `/setup <opción>` - Permite a los administradores activar, desactivar o modificar canales y roles de bienvenida, confesiones, logs, cumpleaños, auto-roles y frases del día de forma sencilla.
* `/play <búsqueda o link>` - Reproduce música de Spotify, YouTube o SoundCloud.
* `/profile` - Muestra tu perfil de usuario, XP acumulada, biografía y monedas del sistema de economía.

---

## ⚙️ Configuración Básica (Administradores)

Configurar el bot es sumamente sencillo gracias al comando `/setup`.
1. **Idioma:** Cambia el idioma en cualquier momento con `/setup lang`.
2. **Canal de Bienvenida:** Actívalo con `/setup welcome <canal>`. Si deseas desactivarlo, simplemente ejecuta el comando sin mencionar ningún canal.
3. **Auto-Rol:** Activa los roles automáticos con `/setup autorole <rol>` y desactívalos ejecutando el comando sin argumentos.
4. **Sistema de Chaos:** Activa o desactiva la ruleta rusa de aislamiento con `/setup chaos <estado> [probabilidad]`.

---

## 🛠️ Detalles Técnicos e Instalación (Para Desarrolladores)

> [!IMPORTANT]
> Esta sección está destinada a personas que deseen hospedar el bot en su propia infraestructura (como un VPS o servidor local).

### Requisitos Previos
* **Python 3.9** o superior.
* Servidor **Lavalink v4+** (para la reproducción de música).
* Credenciales de desarrollador de Discord (Token del Bot).

### Arquitectura y Tecnologías
* **discord.py (v2.0+)** - Framework principal.
* **SQLite3** con `aiosqlite` - Motor de persistencia ultraligero y rápido (WAL habilitado).
* **Wavelink (v3+)** - Conector para el cliente Lavalink de música.
* **aiohttp** - Para el servidor web interno del bridge de Minecraft.

### Instalación

1. **Clonar el proyecto:**
   ```bash
   git clone https://github.com/tu-usuario/discord-bot-py.git
   cd discord-bot-py
   ```

2. **Instalar dependencias:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configurar el Entorno:**
   Crea un archivo `.env` en la raíz del proyecto con la siguiente estructura:
   ```env
   DISCORD_TOKEN=tu_token_de_discord_aqui
   SPOTIFY_CLIENT_ID=opcional_id_cliente_spotify
   SPOTIFY_CLIENT_SECRET=opcional_secreto_cliente_spotify
   PRODUCTION=True
   ```

4. **Ejecutar:**
   ```bash
   python main.py
   ```

### Estructura de Carpetas
* `/cogs` - Capa de presentación (Enrutamiento de comandos tradicionales, Slash Commands y Listeners de eventos).
* `/services` - Capa de lógica de negocio y persistencia (Conexión a DB, multi-idioma, embeds de marca, música, etc.).
* `/ui` - Componentes interactivos de Discord (`discord.ui.View`, `Button`, `Modal`).
* `/config` - Archivos de configuración estática y archivos `.py` de traducción de idiomas.
* `/tools` - Scripts locales de análisis de código AST para validación estática de sintaxis, i18n, comandos y base de datos.