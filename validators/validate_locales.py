import sys
import os
import string

# Append project root to sys.path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(root_dir)

try:
    from config.lang.es import ES
    from config.lang.en import EN
    from config.lang.pt import PT
    from config.lang.fr import FR
except ImportError as e:
    print(f"Error critico: No se pudieron importar los archivos de idioma. {e}")
    sys.exit(1)

def get_placeholders(text):
    """Extrae los marcadores de posición (placeholders) de una cadena de formato."""
    if not isinstance(text, str):
        return set()
    try:
        return {name for _, name, _, _ in string.Formatter().parse(text) if name is not None}
    except Exception:
        return set()

def validate_locales():
    """Compara las llaves y marcadores de los diccionarios de idiomas para detectar discrepancias."""
    langs = {
        "ES.py": set(ES.keys()), 
        "EN.py": set(EN.keys()), 
        "PT.py": set(PT.keys()),
        "FR.py": set(FR.keys())
    }
    all_keys = set().union(*langs.values())
    
    errors_found = False

    print("\n[Locale Validator] Iniciando comprobacion de sincronizacion y marcadores (ES, EN, PT, FR)...")
    print("=" * 60)

    # 1. Validar presencia de llaves en todos los archivos
    for name, keys in langs.items():
        missing = all_keys - keys
        if missing:
            errors_found = True
            print(f"Faltan llaves en {name} [{len(missing)}]:")
            for key in sorted(missing):
                print(f"  - {key}")
            print("-" * 30)

    # 2. Validar consistencia de marcadores de posición (placeholders)
    for key in sorted(all_keys):
        placeholders = {}
        for lang_name, lang_dict in [("ES.py", ES), ("EN.py", EN), ("PT.py", PT), ("FR.py", FR)]:
            if key in lang_dict:
                placeholders[lang_name] = get_placeholders(lang_dict[key])
        
        sets = list(placeholders.values())
        if sets and not all(s == sets[0] for s in sets):
            errors_found = True
            print(f"Discrepancia de marcadores en la llave '{key}':")
            for lang_name, p_set in placeholders.items():
                print(f"  - {lang_name}: {sorted(list(p_set)) if p_set else 'Ninguno'}")
            print("-" * 30)

    if not errors_found:
        print("Perfecto! Todos los archivos de idioma estan 100% sincronizados y sin discrepancias de marcadores.")
        print(f"Total de llaves validadas: {len(all_keys)}")
        sys.exit(0)
    else:
        print("=" * 60)
        print("Se encontraron discrepancias en los archivos de idioma.")
        sys.exit(1)

if __name__ == "__main__":
    validate_locales()
