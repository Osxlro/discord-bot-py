# Directrices de Diseño y Estructura del Portal Web - Friday Bot

Este documento establece las directrices obligatorias de diseño visual, organización de archivos estáticos, enrutamiento de subpáginas y el flujo de autenticación (Discord OAuth2) para el portal web de Friday Bot, inspirado en el diseño moderno e interactivo de **Nekotina**.

---

## 🎨 1. Estética Visual y Componentes (Estilo Nekotina)

El diseño del portal debe ser moderno, fluido y responsivo, utilizando una paleta oscura con acentos vibrantes de color y efectos de desenfoque de fondo.

### Paleta de Colores
* **Fondo de Página (`--bg-color`)**: `#0f111a` (azul oscuro profundo).
* **Fondo de Tarjetas (`--card-bg`)**: `rgba(255, 255, 255, 0.03)` (efecto esmerilado translúcido).
* **Color Primario (`--primary-color`)**: `#5865F2` (azul Discord blurple).
* **Acentuación / Destacados**: Gradients lineales fluidos (ej. `#8b5cf6` a `#ec4899`).
* **Estado Activo (`--online-color`)**: `#22c55e` (verde brillante con pulso).

### Tipografía
* Utilizar **Outfit** o **Inter** desde Google Fonts para textos generales y títulos.
* Evitar fuentes por defecto del navegador para mantener el diseño premium.

### Efectos y Transiciones
* **Glassmorphism**: Uso de `backdrop-filter: blur(16px)` en tarjetas y barras de navegación.
* **Micro-animaciones**: Transiciones suaves (`transition: all 0.3s ease`) en botones y enlaces.

---

## 📁 2. Estructura de Carpetas para Estáticos y Subpáginas

Para mantener el código ordenado y separado de la lógica del bot, seguiremos este esquema de directorios bajo `/web/`:

```
/web/
├── app.py                # Inicialización de FastAPI y Middlewares
├── server.py             # Clase controladora de Uvicorn
├── config/
│   └── web_settings.py   # Variables de entorno y configuraciones web
├── static/               # Recursos Estáticos
│   ├── css/
│   │   ├── main.css      # Estilos generales y tokens globales
│   │   ├── docs.css      # Estilos específicos de documentación
│   │   └── profile.css   # Estilos del dashboard del usuario
│   ├── js/
│   │   └── main.js       # Interactividad del lado del cliente
│   └── images/           # Logos, banners e iconos
└── templates/            # Plantillas Jinja2
    ├── base.html         # Plantilla base (Navbar, Footer, CSS)
    ├── index.html        # Página de inicio
    ├── commands.html     # Listado interactivo de comandos (/commands)
    ├── docs.html         # Documentación de configuración (/docs)
    ├── profile.html      # Panel privado del usuario (/profile)
    └── legacy_v1.html    # Archivo histórico preservando el origen
```

---

## 🔗 3. Enrutamiento y Subpáginas
Todas las rutas deben responder a URL semánticas y amigables:
1. **`/` (Inicio)**: Presentación del bot, botón de invitación, enlace al soporte y estadísticas rápidas.
2. **`/commands` (Comandos)**: Buscador y listado categorizado de comandos (ej. Música, Niveles, Diversión) consumidos dinámicamente de `bot.commands`.
3. **`/docs` (Documentación)**: Guías detalladas sobre configuración de canales, sistema de XP y roles.
4. **`/profile` (Usuario)**: Panel privado del usuario tras iniciar sesión.

---

## 🔐 4. Flujo Conceptual del Login (Discord OAuth2)

Para permitir a los usuarios gestionar sus datos (cumpleaños, biografía, desvincular cuenta) de forma segura y sin necesidad de un dashboard complejo, implementaremos el login nativo de Discord:

### Diagrama del Flujo OAuth2:

```
Usuario Click "Login" ---> Redirige a Discord Auth URL
  ---> Usuario Autoriza ---> Redirige a Web con code
  ---> Web cambia code por token ---> Obtiene datos del usuario (identify)
  ---> Web crea sesión segura (Cookie/JWT) ---> Muestra perfil /profile
```

### Gestión de Datos en el Dashboard:
Una vez logeado, el usuario podrá ver una interfaz minimalista donde:
1. **Visualizar Datos**: Ver sus coins actuales, fecha de cumpleaños guardada y biografía establecida.
2. **Borrar Datos**: Un botón de "Eliminar mis datos" que ejecuta una consulta DELETE en la base de datos (mediante `UserRepository.delete_user_birthday` y similares) garantizando el derecho de borrado y privacidad.
3. **Modificar Preferencias**: Configurar la privacidad de su cumpleaños (Visible/Oculto) de forma visual.
