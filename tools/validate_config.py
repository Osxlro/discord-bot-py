import os
import sys

# Set project root to sys.path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(root_dir)

def validate_config():
    print("\n[Config Validator] Iniciando comprobacion de configuracion y entorno...")
    print("=" * 60)

    errors_found = False

    # 1. Comprobar archivo .env
    print("[Config Validator] Verificando existencia de archivo .env...")
    env_path = os.path.join(root_dir, ".env")
    if not os.path.exists(env_path):
        print("[WARNING] No se encontro el archivo .env en la raiz del proyecto.")
        print("          Asegurate de definir las variables de entorno en tu sistema.")
    else:
        print("[Config Validator] Archivo .env encontrado.")

    # 2. Comprobar variables de entorno obligatorias
    print("[Config Validator] Validando variables de entorno obligatorias...")
    mandatory_vars = ["DISCORD_TOKEN"]
    for var in mandatory_vars:
        val = os.getenv(var)
        # Si no esta cargada en os.getenv, intentar leerla manualmente de .env por si acaso
        if not val and os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip().startswith(var + "="):
                        val = line.split("=", 1)[1].strip()
                        break
        
        if not val:
            errors_found = True
            print(f"[ERROR] Variable de entorno obligatoria faltante: {var}")
        else:
            masked = val[:4] + "..." + val[-4:] if len(val) > 8 else "********"
            print(f"  - {var}: {masked} (Cargada correctamente)")

    # 3. Comprobar variables de entorno opcionales pero recomendadas
    print("[Config Validator] Validando variables de entorno opcionales...")
    optional_vars = ["SPOTIFY_CLIENT_ID", "SPOTIFY_CLIENT_SECRET", "PRODUCTION"]
    for var in optional_vars:
        val = os.getenv(var)
        if not val and os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip().startswith(var + "="):
                        val = line.split("=", 1)[1].strip()
                        break
        if not val:
            print(f"  - {var}: NO CONFIGURADA (Opcional)")
        else:
            print(f"  - {var}: CONFIGURADA")

    # 4. Importar y comprobar settings.py
    print("[Config Validator] Cargando modulo config/settings.py...")
    try:
        from config import settings
        print("[Config Validator] Modulo config/settings.py cargado con exito.")
        
        # Verificar estructuras basicas de configuracion
        required_settings = ["CONFIG", "COLORS", "DB_CONFIG", "UI_CONFIG"]
        for key in required_settings:
            if not hasattr(settings, key):
                errors_found = True
                print(f"[ERROR] Estructura faltante en settings.py: {key}")
            else:
                print(f"  - settings.{key}: OK")
    except Exception as e:
        errors_found = True
        print(f"[ERROR] Fallo critico al cargar config/settings.py: {e}")

    if not errors_found:
        print("Perfecto! La configuracion y las variables de entorno son consistentes.")
        sys.exit(0)
    else:
        print("=" * 60)
        print("Se encontraron errores o faltas en la configuracion del sistema.")
        sys.exit(1)

if __name__ == "__main__":
    validate_config()
