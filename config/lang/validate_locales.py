import sys
import os

# Asegurar que el directorio raíz esté en el path para poder importar el paquete config
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    from config.lang.es import ES
    from config.lang.en import EN
    from config.lang.pt import PT
    from config.lang.fr import FR
except ImportError as e:
    print(f"Error critico: No se pudieron importar los archivos de idioma. {e}")
    sys.exit(1)

def validate_locales():
    """Compara las llaves de los diccionarios de idiomas para detectar faltantes."""
    langs = {
        "ES.py": set(ES.keys()), 
        "EN.py": set(EN.keys()), 
        "PT.py": set(PT.keys()),
        "FR.py": set(FR.keys())
    }
    all_keys = set().union(*langs.values())
    
    errors_found = False

    print("\n[Locale Validator] Iniciando comprobacion de sincronizacion (ES, EN, PT, FR)...")
    print("=" * 60)

    for name, keys in langs.items():
        missing = all_keys - keys
        if missing:
            errors_found = True
            print(f"Faltan en {name} [{len(missing)}]:")
            for key in sorted(missing):
                print(f"  - {key}")
            print("-" * 30)

    if not errors_found:
        print("Perfecto! Todos los archivos de idioma estan 100% sincronizados.")
        print(f"Total de llaves validadas: {len(all_keys)}")
    else:
        print("=" * 60)
        print("Se encontraron discrepancias en los archivos de idioma.")
        sys.exit(1)

if __name__ == "__main__":
    validate_locales()
