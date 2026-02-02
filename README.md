# 🤖 Discord Bot Py

[!Python Version](https://www.python.org/)
[!discord.py](https://github.com/Rapptz/discord.py)
[!License](LICENSE)

Un bot de Discord modular, multilingüe y optimizado, diseñado para ofrecer una gestión integral de comunidades con un consumo mínimo de recursos. Ideal para despliegues en VPS pequeños.

---

## 📌 Tabla de Contenidos
- Características Principales
- Tecnologías Utilizadas
- Requisitos Previos
- Instalación y Configuración
- Estructura del Proyecto
- Comandos Destacados
- Contribución

---

## ✨ Características Principales

### 📈 Sistema de Niveles y Experiencia
* **Progresión Dinámica:** Algoritmo de XP exponencial para mantener el interés a largo plazo.
* **Sistema de Prestigio (Rebirth):** Los usuarios pueden reiniciar su nivel al llegar al 100 para obtener marcas de prestigio.
* **Optimización de I/O:** Sistema de caché inteligente que agrupa escrituras en la base de datos para reducir el desgaste del disco.
* **Perfiles Visuales:** Comandos para consultar rangos y estadísticas personales.

### 🎵 Sistema de Música (Nuevo)
* **Alta Calidad:** Reproducción de música utilizando **Lavalink** (Wavelink) para un rendimiento óptimo sin lag.
* **Control Total:** Comandos intuitivos (`/play`, `/pause`, `/skip`, `/volume`) y panel de botones interactivos.
* **Funciones Avanzadas:** Soporte para **Autoplay** (reproducción infinita), **Loop** (pista/cola), **Shuffle** y búsqueda con autocompletado.
* **Listas de Reproducción:** Gestión de colas con paginación para servidores con mucha actividad.

### 🛡️ Moderación y Administración
* **Herramientas de Gestión:** Comandos de `kick`, `ban`, `clear` y `timeout` con soporte para jerarquías de roles.
* **Auto-Roles:** Asignación automática de roles configurables al unirse nuevos miembros.
* **Logs y Auditoría:** Registro detallado de eventos importantes y acciones administrativas.
* **Gestión de Estados:** Sistema rotativo de presencia configurable mediante menús interactivos.

### 🎮 Integración con Minecraft
* **Bridge Bidireccional:** Servidor web interno (`aiohttp`) que permite la comunicación entre el chat de Discord y el servidor de Minecraft.
* **Seguridad Mejorada:** Validación de Tokens y payloads para evitar accesos no autorizados.
* **Robustez:** Selección automática de puertos y manejo de errores de conexión.
* **Estadísticas en Tiempo Real:** Visualización de vida, bioma, coordenadas y XP del jugador desde Discord.

### ⚙️ Utilidades y Configuración
* **Multi-idioma:** Soporte nativo para múltiples idiomas mediante un sistema de localización centralizado.
* **Backups Automáticos:** Copias de seguridad de la base de datos enviadas directamente al DM del propietario cada 12 horas.
* **Modo de Voz AFK:** Mantiene al bot conectado en canales de voz con consumo de recursos nulo.
* **Estabilidad:** Sistema de reconexión automática de voz y protección contra fugas de memoria (RAM).

---

## 🛠️ Tecnologías Utilizadas
* **Lenguaje:** Python 3.9+
* **Librería Principal:** discord.py
* **Base de Datos:** SQLite3
* **Música:** Wavelink (Cliente Lavalink)
* **Servidor Web:** aiohttp (para el bridge de Minecraft)
* **Gestión de Entorno:** python-dotenv

---

## Requisitos Previos
* Python 3.9 o superior.
* Servidor Lavalink (v4+) para el módulo de música (Local o Externo).
* Una cuenta de desarrollador de Discord y un Token de Bot.

---

## 🚀 Instalación y Configuración

### 1. Clonar el repositorio
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