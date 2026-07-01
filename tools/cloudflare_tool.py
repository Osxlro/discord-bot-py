import argparse
import sys
import json
import requests
import io
import os
from dotenv import load_dotenv

# Cargar variables de entorno del archivo .env
load_dotenv()

# Force UTF-8 encoding for standard output to avoid Windows console errors
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Credenciales de Cloudflare
CLOUDFLARE_ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID", "370304a901f5aad1dfac5afb1e3c7c8d")
CLOUDFLARE_API_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN")

if not CLOUDFLARE_API_TOKEN:
    # Intento de fallback al token proporcionado si no se encuentra en el entorno
    # pero sin exponerlo en texto plano directamente al subir al repositorio
    CLOUDFLARE_API_TOKEN = os.environ.get("CLOUDFLARE_API_TOKEN", "")

BASE_URL = "https://api.cloudflare.com/client/v4"

def get_headers():
    return {
        "Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}",
        "Content-Type": "application/json"
    }

def list_zones():
    """Listar las zonas DNS registradas en la cuenta."""
    print("🌐 Consultando zonas DNS en Cloudflare...")
    url = f"{BASE_URL}/zones"
    try:
        response = requests.get(url, headers=get_headers())
        if response.status_code == 200:
            zones = response.json().get("result", [])
            print(f"✅ Se encontraron {len(zones)} zonas:")
            for z in zones:
                print(f"  - [{z['id']}] {z['name']} (Estado: {z['status']})")
        else:
            print(f"❌ Error al consultar zonas ({response.status_code}): {response.text}")
    except Exception as e:
        print(f"❌ Excepcion al listar zonas: {e}")

def purge_cache(zone_id: str):
    """Purgar toda la cache para una zona DNS."""
    print(f"🧹 Purgando cache para la zona {zone_id}...")
    url = f"{BASE_URL}/zones/{zone_id}/purge_cache"
    payload = {"purge_everything": True}
    try:
        response = requests.post(url, headers=get_headers(), json=payload)
        if response.status_code == 200:
            print("✅ Cache purgada exitosamente en Cloudflare.")
        else:
            print(f"❌ Error al purgar cache ({response.status_code}): {response.text}")
    except Exception as e:
        print(f"❌ Excepcion al purgar cache: {e}")

def list_dns_records(zone_id: str):
    """Listar los registros DNS de una zona en específico."""
    print(f"📝 Consultando registros DNS para la zona {zone_id}...")
    url = f"{BASE_URL}/zones/{zone_id}/dns_records"
    try:
        response = requests.get(url, headers=get_headers())
        if response.status_code == 200:
            records = response.json().get("result", [])
            print(f"✅ Se encontraron {len(records)} registros:")
            for r in records:
                print(f"  - [{r['id']}] {r['type']} {r['name']} -> {r['content']} (Proxied: {r['proxied']})")
        else:
            print(f"❌ Error al consultar registros DNS ({response.status_code}): {response.text}")
    except Exception as e:
        print(f"❌ Excepcion al consultar registros DNS: {e}")

# --- OPERACIONES CLOUDFLARE R2 BUCKETS ---

def list_r2_buckets():
    """Listar los buckets R2 de almacenamiento."""
    print("📦 Consultando buckets de R2 en Cloudflare...")
    url = f"{BASE_URL}/accounts/{CLOUDFLARE_ACCOUNT_ID}/r2/buckets"
    try:
        response = requests.get(url, headers=get_headers())
        if response.status_code == 200:
            buckets = response.json().get("result", {}).get("buckets", [])
            print(f"✅ Se encontraron {len(buckets)} buckets R2:")
            for b in buckets:
                print(f"  - {b['name']} (Creado: {b['creation_date']})")
        else:
            print(f"❌ Error al consultar buckets ({response.status_code}): {response.text}")
    except Exception as e:
        print(f"❌ Excepcion al listar buckets: {e}")

def create_r2_bucket(bucket_name: str):
    """Crear un nuevo bucket R2."""
    print(f"🚀 Creando bucket R2 '{bucket_name}'...")
    url = f"{BASE_URL}/accounts/{CLOUDFLARE_ACCOUNT_ID}/r2/buckets"
    payload = {"name": bucket_name}
    try:
        response = requests.post(url, headers=get_headers(), json=payload)
        if response.status_code == 200:
            print(f"✅ Bucket R2 '{bucket_name}' creado con exito.")
        else:
            print(f"❌ Error al crear bucket ({response.status_code}): {response.text}")
    except Exception as e:
        print(f"❌ Excepcion al crear bucket: {e}")

def delete_r2_bucket(bucket_name: str):
    """Eliminar un bucket R2."""
    print(f"🗑️ Eliminando bucket R2 '{bucket_name}'...")
    url = f"{BASE_URL}/accounts/{CLOUDFLARE_ACCOUNT_ID}/r2/buckets/{bucket_name}"
    try:
        response = requests.delete(url, headers=get_headers())
        if response.status_code == 200:
            print(f"✅ Bucket R2 '{bucket_name}' eliminado con exito.")
        else:
            print(f"❌ Error al eliminar bucket ({response.status_code}): {response.text}")
    except Exception as e:
        print(f"❌ Excepcion al eliminar bucket: {e}")

def main():
    parser = argparse.ArgumentParser(description="Herramienta CLI/MCP para administracion de Cloudflare y R2.")
    
    # Comandos de DNS/Zonas
    parser.add_argument("--zones", action="store_true", help="Listar todas las zonas DNS registradas.")
    parser.add_argument("--purge-cache", metavar="ZONE_ID", help="Purgar la cache completa de la zona dada.")
    parser.add_argument("--dns-records", metavar="ZONE_ID", help="Listar los registros DNS de la zona dada.")
    
    # Comandos de R2
    parser.add_argument("--r2-list", action="store_true", help="Listar todos los buckets R2 de la cuenta.")
    parser.add_argument("--r2-create", metavar="BUCKET_NAME", help="Crear un nuevo bucket R2.")
    parser.add_argument("--r2-delete", metavar="BUCKET_NAME", help="Eliminar un bucket R2 existente.")

    args = parser.parse_args()

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)

    if args.zones:
        list_zones()
    elif args.purge_cache:
        purge_cache(args.purge_cache)
    elif args.dns_records:
        list_dns_records(args.dns_records)
    elif args.r2_list:
        list_r2_buckets()
    elif args.r2_create:
        create_r2_bucket(args.r2_create)
    elif args.r2_delete:
        delete_r2_bucket(args.r2_delete)

if __name__ == "__main__":
    main()
