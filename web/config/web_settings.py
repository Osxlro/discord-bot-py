import os
from dotenv import load_dotenv

# Cargar variables de entorno del archivo .env
load_dotenv()

# Configuración del servidor web
WEB_HOST = os.getenv("WEB_HOST", "0.0.0.0")
WEB_PORT = int(os.getenv("WEB_PORT", "5058"))
WEB_DOMAIN = os.getenv("WEB_DOMAIN", "fridaybot.duckdns.org")
WEB_EXPOSE_PORT = os.getenv("WEB_EXPOSE_PORT", "True") == "True"

# Credenciales de Discord OAuth2 (para el futuro Login)
DISCORD_CLIENT_ID = os.getenv("DISCORD_CLIENT_ID", "")
DISCORD_CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET", "")
