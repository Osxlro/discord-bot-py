import os
import sys
import re

# Asegurar compatibilidad de salida de consola
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def main():
    print("[Web Validator] Iniciando comprobacion de consistencia y traduccion...")
    print("============================================================")
    
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    templates_dir = os.path.join(root_dir, "web", "templates")
    translations_path = os.path.join(root_dir, "web", "static", "js", "translations.js")
    
    if not os.path.exists(templates_dir):
        print(f"Error critico: Directorio de plantillas no encontrado en {templates_dir}")
        sys.exit(1)
        
    if not os.path.exists(translations_path):
        print(f"Error critico: Archivo de traducciones no encontrado en {translations_path}")
        sys.exit(1)
        
    # 1. Escanear llaves data-i18n utilizadas en las plantillas HTML
    used_keys = set()
    html_files = []
    
    for root, _, files in os.walk(templates_dir):
        for file in files:
            if file.endswith(".html"):
                html_files.append(os.path.join(root, file))
                
    key_regex = re.compile(r'data-i18n=["\']([a-zA-Z0-9_-]+)["\']')
    
    for filepath in html_files:
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                html_content = f.read()
                matches = key_regex.findall(html_content)
                used_keys.update(matches)
        except Exception as e:
            print(f"Error leyendo plantilla {os.path.basename(filepath)}: {e}")
            
    print(f"[Web Validator] Se encontraron {len(used_keys)} llaves de traduccion en uso en {len(html_files)} plantillas HTML.")
    
    # 2. Cargar y parsear translations.js
    try:
        with open(translations_path, "r", encoding="utf-8") as f:
            js_content = f.read()
    except Exception as e:
        print(f"Error critico leyendo translations.js: {e}")
        sys.exit(1)
        
    langs = ["es", "en", "pt", "fr"]
    lang_keys = {}
    
    for lang in langs:
        # Encontrar el inicio del bloque de idioma (ej: es: {)
        start_match = re.search(fr"\b{lang}:\s*\{{", js_content)
        if start_match:
            start_idx = start_match.end()
            bracket_count = 1
            end_idx = start_idx
            
            while bracket_count > 0 and end_idx < len(js_content):
                if js_content[end_idx] == "{":
                    bracket_count += 1
                elif js_content[end_idx] == "}":
                    bracket_count -= 1
                end_idx += 1
                
            block = js_content[start_idx:end_idx-1]
            # Extraer llaves en formato key: "value", asegurando coincidir solo al inicio de la linea (evita falsos positivos con dos puntos en las cadenas)
            keys = re.findall(r"^\s*([a-zA-Z0-9_-]+)\s*:", block, re.MULTILINE)
            lang_keys[lang] = set(keys)
        else:
            lang_keys[lang] = set()
            
    # 3. Analizar consistencia y discrepancias
    has_errors = False
    
    # Comprobar consistencia entre los propios idiomas
    all_defined_keys = set()
    for lang, keys in lang_keys.items():
        all_defined_keys.update(keys)
        
    for lang in langs:
        missing_in_lang = all_defined_keys - lang_keys[lang]
        if missing_in_lang:
            print(f"[ERROR] Llaves definidas en otros idiomas pero faltantes en '{lang}':")
            for k in sorted(missing_in_lang):
                print(f"  - {k}")
            has_errors = True
            
    # Comprobar que todas las llaves usadas en el HTML existan en translations.js
    missing_in_translations = used_keys - all_defined_keys
    if missing_in_translations:
        print("[ERROR] Llaves utilizadas en HTML (data-i18n) pero no definidas en translations.js:")
        for k in sorted(missing_in_translations):
            print(f"  - {k}")
        has_errors = True
        
    # Comprobar si hay llaves no usadas en translations.js (solo advertencia)
    unused_keys = all_defined_keys - used_keys
    # Excluir de no usadas las llaves que se determinan de forma dinamica (como los tipos de comandos o titulos dinamicos de la web)
    dynamic_exclusions = {
        "web_home", "web_commands", "web_docs_title", "web_profile_title",
        "web_terms_of_service", "web_privacy_policy", "cmd_type_hybrid",
        "cmd_type_slash", "cmd_type_prefix"
    }
    unused_keys -= dynamic_exclusions
    
    if unused_keys:
        print(f"[WARNING] Se encontraron {len(unused_keys)} llaves definidas en translations.js aparentemente no usadas:")
        for k in sorted(unused_keys):
            print(f"  - {k}")
            
    print("------------------------------------------------------------")
    if has_errors:
        print("[Web Validator] Se encontraron errores de consistencia. Verificacion fallida.")
        sys.exit(1)
    else:
        print("[Web Validator] Perfecto! El frontend web esta consistente y traducido al 100%.")
        sys.exit(0)

if __name__ == "__main__":
    main()
