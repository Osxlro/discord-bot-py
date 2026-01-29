# Discord Bot Py

Un bot de Discord modular y optimizado escrito en Python utilizando `discord.py`. Este proyecto está diseñado para ser eficiente en el consumo de recursos (ideal para VPS pequeños) y ofrece un sistema completo de gestión de comunidades, niveles y utilidades.

## Características Principales

El bot está dividido en módulos (Cogs) para facilitar su mantenimiento y escalabilidad.

### Sistema de Niveles y Experiencia

* **Progresión Exponencial:** Sistema de XP calculado para aumentar la dificultad progresivamente.
* **Sistema de Renacimiento (Rebirth):** Permite a los usuarios reiniciar su nivel al llegar al 100 a cambio de marcas de prestigio.
* **Rankings y Perfiles:** Comandos para visualizar tablas de clasificación y tarjetas de perfil personalizables.
* **Optimización de I/O:** Implementa un sistema de caché en memoria RAM para reducir las escrituras en disco (base de datos), guardando datos por intervalos.

### Moderación y Administración

* **Herramientas de Moderación:** Comandos estándar para expulsar, banear y limpiar mensajes masivamente.
* **Auto-Roles:** Asignación automática de roles a nuevos usuarios.
* **Logs y Auditoría:** Registro de eventos importantes del servidor.
* **Gestión de Estados:** Sistema rotativo de presencia del bot, configurable mediante comandos con menús interactivos.

### Utilidades y Configuración

* **Configuración por Servidor:** Panel de ajustes para personalizar canales de bienvenida, mensajes de nivel, idiomas y roles.
* **Modo de Voz AFK:** Funcionalidad para mantener al bot conectado en canales de voz con consumo de recursos nulo (modo sordo/muteado).
* **Copias de Seguridad:** Tareas automáticas de respaldo de la base de datos enviadas al propietario.
* **Sistema de Ayuda Dinámico:** Menú de ayuda que se actualiza automáticamente según los módulos cargados.

## Requisitos Previos

* Python 3.9 o superior.
* Una cuenta de desarrollador de Discord y un Token de Bot.

## Instalación

Sigue estos pasos para desplegar el bot en tu entorno local o servidor.

1. **Clonar el repositorio:**
```bash
git clone https://github.com/tu-usuario/discord-bot-py.git
cd discord-bot-py

```


2. **Instalar dependencias:**
Se recomienda utilizar un entorno virtual.
```bash
pip install -r requirements.txt

```


3. **Configuración del entorno:**
Crea un archivo llamado `.env` en la raíz del proyecto y define las siguientes variables:
```env
DISCORD_TOKEN=tu_token_aqui

```


4. **Base de Datos:**
El bot utiliza SQLite (`data/database.sqlite3`). El sistema inicializará la base de datos y las tablas necesarias automáticamente en la primera ejecución.

## Ejecución

Para iniciar el bot, ejecuta el archivo principal:

```bash
python main.py

```

## Estructura del Proyecto

* `/cogs`: Contiene todos los módulos de comandos y eventos.
* `/config`: Archivos de configuración y textos de localización (idiomas).
* `/services`: Lógica de negocio reutilizable (Base de datos, Embeds, Idiomas).
* `/data`: Almacenamiento de la base de datos SQLite y logs.

---