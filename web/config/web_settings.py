import os
from dotenv import load_dotenv

# Cargar variables de entorno del archivo .env
load_dotenv()

# Configuración del servidor web
WEB_HOST = os.getenv("WEB_HOST", "0.0.0.0")
WEB_PORT = int(os.getenv("WEB_PORT", "5058"))
WEB_DOMAIN = os.getenv("WEB_DOMAIN", "friday.oscurin.uk")
WEB_EXPOSE_PORT = os.getenv("WEB_EXPOSE_PORT", "True") == "True"

import base64

# Credenciales de Discord OAuth2 (para el futuro Login)
DISCORD_CLIENT_ID = os.getenv("DISCORD_CLIENT_ID", "")
if not DISCORD_CLIENT_ID:
    token = os.getenv("DISCORD_TOKEN", "")
    if token:
        try:
            first_part = token.split(".")[0]
            first_part += "=" * (4 - len(first_part) % 4)
            DISCORD_CLIENT_ID = base64.b64decode(first_part.encode("utf-8")).decode("utf-8")
        except Exception:
            pass
DISCORD_CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET", "")

# Ajustes de sesión y cookies
SESSION_SECRET_KEY = os.getenv("SESSION_SECRET_KEY", "FridayBotWebSessionCryptedKey2026_Secure")
WEB_SECURE_COOKIES = os.getenv("WEB_SECURE_COOKIES", "False").lower() == "true"
