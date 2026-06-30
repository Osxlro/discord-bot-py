# Directrices de Diseño y Estructura del Portal Web - Friday Bot

Este documento establece las directrices obligatorias de diseño visual, organización de archivos estáticos, enrutamiento de subpáginas y el flujo de autenticación (Discord OAuth2) para el portal web de Friday Bot, inspirado en la fusión de **Frutiger Aero** y **Glassmorphism** (estilo MEE6, Nekotina y Dank Memer).

---

## 🎨 1. Estética Visual: Frutiger Aero + Glassmorphism

El diseño visual busca dar una sensación orgánica, brillante y cristalina de alta tecnología.

### Paleta de Colores
* **Fondo Base (`--bg-color`)**: `#0b132b` (azul noche/océano profundo).
* **Fondo de Tarjetas (`--card-bg`)**: `rgba(255, 255, 255, 0.04)` (vidrio translúcido).
* **Acentuación Primaria (`--primary-color`)**: `#00c6ff` a `#0072ff` (azul brillante con gloss).
* **Acentuación Secundaria (`--accent-color`)**: `#38ef7d` (verde lima brillante).

### Principios de Diseño
1. **Glassmorphism**: Todos los contenedores importantes deben llevar `backdrop-filter: blur(24px)` y un borde blanco semitransparente con `box-shadow` interna sutil para simular el brillo del vidrio.
2. **Frutiger Aero Elements**:
   * Fondo con auroras suaves usando degradados radiales.
   * Burbujas animadas y flotantes en el fondo mediante animaciones de transición en CSS (`floatUp`).
   * Botones brillantes estilo skeuomorphic con efecto tridimensional en el color de fondo y sombreado.
3. **Bento Grid Layout**:
   * Los dashboards (como `/profile`) deben estar estructurados como Bento Grids con cajas de proporciones variables (`bento-box`) para dividir visualmente la información del usuario de forma organizada.
4. **Responsividad (Mobile-First)**:
   * La barra de navegación debe envolver sus elementos para pantallas pequeñas.
   * Los grids de estadísticas y el listado de comandos deben colapsar a una columna en dispositivos móviles.
5. **Estilos Defensivos Inline**:
   * Para evitar el desorden visual en el navegador del cliente si el CSS tarda en cargar o se carga desde la caché del navegador, todos los componentes de imágenes e iconos críticos deben llevar tamaños fijos definidos directamente en atributos de estilo inline en el HTML (ej: `style="width: 42px; height: 42px; overflow: hidden; object-fit: cover;"`).
6. **Iconografía Vectorial**:
   * Siguiendo la regla `no-emoji-icons`, los emojis planos deben evitarse en favor de iconos vectoriales SVG limpios y nítidos.

---

## 📁 2. Estructura de Carpetas para Estáticos y Subpáginas

Para mantener el código ordenado y separado de la lógica del bot, seguiremos este esquema de directorios bajo `/web/`:

```
/web/
├── app.py                # Inicialización de FastAPI, Middlewares y Enrutamiento
├── server.py             # Clase controladora de Uvicorn y Configuración SSL
├── DESIGN.md             # Guías de diseño y estilos de interfaz (Este archivo)
├── config/
│   └── web_settings.py   # Variables de entorno y configuraciones web
├── static/               # Recursos Estáticos
│   ├── css/
│   │   ├── main.css      # Estilos generales, animaciones Frutiger Aero y media queries
│   │   ├── docs.css      # Estilos específicos de documentación
│   │   └── profile.css   # Estilos del dashboard del usuario
│   ├── js/
│   │   ├── main.js       # Interactividad del lado del cliente
│   │   ├── translations.js # Diccionarios de traducción local
│   │   └── i18n.js       # Motor de traducción DOM del cliente
│   └── images/           # Logos, banners e iconos
└── templates/            # Plantillas Jinja2
    ├── base.html         # Plantilla base (Navbar, Footer, Burbujas de fondo, CSS)
    ├── index.html        # Página de inicio
    ├── commands.html     # Listado interactivo de comandos (/commands)
    ├── docs.html         # Documentación de configuración (/docs)
    ├── profile.html      # Panel privado del usuario (/profile)
    ├── terms.html        # Términos de Servicio del bot (/terms)
    ├── privacy.html      # Política de Privacidad y Derechos de Borrado (/privacy)
    └── legacy_v1.html    # Archivo histórico de la versión original
```

---

## 🔗 3. Enrutamiento y Subpáginas
Todas las rutas deben responder a URL semánticas y amigables:
1. **`/` (Inicio)**: Presentación del bot, botón de invitación y estadísticas en tiempo real.
2. **`/commands` (Comandos)**: Listado dinámico categorizado por cogs con tags de colores.
3. **`/docs` (Documentación)**: Guías de configuración.
4. **`/profile` (Usuario)**: Panel privado del usuario con Bento Grid y configuración de perfil.
5. **`/terms` (Términos)**: Aspectos legales sobre el uso aceptable y limitaciones del bot.
6. **`/privacy` (Privacidad)**: Transparencia de almacenamiento de datos de base de datos y derechos.

---

## 🔒 4. Autenticación y Seguridad (OAuth2)
1. **Verificación Anti-CSRF (State Parameter)**:
   * El flujo de inicio de sesión debe generar un token de estado seguro y aleatorio (`secrets.token_urlsafe(16)`), guardarlo en la cookie de sesión cifrada del usuario y verificarlo contra el parámetro `state` recibido en `/auth/callback`. Si no coincide, rechazar la solicitud con un código HTTP `400 Bad Request`.
2. **Dynamic Client ID Fallback**:
   * Si no se define `DISCORD_CLIENT_ID` en el entorno de producción, el sistema debe extraerlo dinámicamente decodificando la carga útil del primer bloque en Base64 de `DISCORD_TOKEN`, o bien consultando a la instancia del bot mediante `bot.user.id`.

---

## 🌐 5. Internacionalización en el Frontend
* **Traducción del DOM**: Queda estrictamente prohibido usar texto estático hardcodeado en las plantillas HTML. Toda cadena de texto del lado del cliente debe cargarse mediante el atributo `data-i18n="clave_traduccion"` para que el motor `i18n.js` la asocie dinámicamente con los diccionarios localizados en `translations.js`.
* **Evitar textContent Destructivo**: Para los textos que contengan formato HTML (como negrita `<strong>` o saltos de línea `<br>`), los elementos que contengan texto estático deben subdividirse en etiquetas translatables individuales de forma que `textContent` no destruya la estructura HTML original.
