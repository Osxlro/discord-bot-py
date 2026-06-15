import sys
import os
import string
import ast

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

class GetTextVisitor(ast.NodeVisitor):
    def __init__(self, filepath):
        self.filepath = filepath
        self.calls = []

    def visit_Call(self, node):
        is_get_text = False
        if isinstance(node.func, ast.Name) and node.func.id == "get_text":
            is_get_text = True
        elif isinstance(node.func, ast.Attribute) and node.func.attr == "get_text":
            is_get_text = True
            
        if is_get_text and node.args:
            first_arg = node.args[0]
            key = None
            if isinstance(first_arg, ast.Constant):
                key = first_arg.value
            elif isinstance(first_arg, ast.Str): # Support Python < 3.8
                key = first_arg.s
                
            kwargs = []
            has_double_starred = False
            for kw in node.keywords:
                if kw.arg is None:
                    has_double_starred = True
                else:
                    kwargs.append(kw.arg)
                    
            self.calls.append({
                "key": key,
                "kwargs": kwargs,
                "has_double_starred": has_double_starred,
                "line": node.lineno,
                "col": node.col_offset,
                "filepath": self.filepath
            })
        self.generic_visit(node)

def scan_code_for_i18n():
    """Escanea el código fuente buscando llamadas a get_text."""
    target_dirs = ["cogs", "services", "ui", "config"]
    target_files = ["main.py"]
    
    files_to_check = []
    for directory in target_dirs:
        dir_path = os.path.join(root_dir, directory)
        if not os.path.exists(dir_path):
            continue
        for r, _, files in os.walk(dir_path):
            # Omitir la carpeta de idiomas para no auto-escanear
            if "lang" in r:
                continue
            for file in files:
                if file.endswith(".py"):
                    files_to_check.append(os.path.join(r, file))
                    
    for file in target_files:
        file_path = os.path.join(root_dir, file)
        if os.path.exists(file_path):
            files_to_check.append(file_path)
            
    all_calls = []
    for filepath in files_to_check:
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                source = f.read()
            tree = ast.parse(source, filename=filepath)
            visitor = GetTextVisitor(filepath)
            visitor.visit(tree)
            all_calls.extend(visitor.calls)
        except Exception as e:
            print(f"Advertencia: No se pudo parsear {filepath} para i18n: {e}")
            
    return all_calls

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

    # 1. Validar presencia de llaves en todos los archivos de traducción
    for name, keys in langs.items():
        missing = all_keys - keys
        if missing:
            errors_found = True
            print(f"[ERROR] Faltan llaves en {name} [{len(missing)}]:")
            for key in sorted(missing):
                print(f"  - {key}")
            print("-" * 30)

    # 2. Validar consistencia de marcadores de posición en traducciones
    for key in sorted(all_keys):
        placeholders = {}
        for lang_name, lang_dict in [("ES.py", ES), ("EN.py", EN), ("PT.py", PT), ("FR.py", FR)]:
            if key in lang_dict:
                placeholders[lang_name] = get_placeholders(lang_dict[key])
        
        sets = list(placeholders.values())
        if sets and not all(s == sets[0] for s in sets):
            errors_found = True
            print(f"[ERROR] Discrepancia de marcadores en la llave '{key}':")
            for lang_name, p_set in placeholders.items():
                print(f"  - {lang_name}: {sorted(list(p_set)) if p_set else 'Ninguno'}")
            print("-" * 30)

    # 3. Validar integridad de las llamadas en el código real
    print("[Locale Validator] Escaneando llamadas get_text en el código...")
    code_calls = scan_code_for_i18n()
    used_keys = set()
    
    for call in code_calls:
        key = call["key"]
        if key is None:
            continue # Clave dinámica (no literal), no se puede validar estáticamente
            
        used_keys.add(key)
        
        # Validar si la clave existe en las traducciones
        if key not in all_keys:
            errors_found = True
            rel_path = os.path.relpath(call["filepath"], root_dir)
            print(f"[ERROR] Clave inexistente en traducciones: '{key}' usada en {rel_path} (Línea {call['line']})")
            continue
            
        # Validar marcadores de posición si no hay unpacking dinámico (**kwargs)
        if not call["has_double_starred"]:
            # Obtener los marcadores requeridos por la traducción base (ES)
            required_placeholders = get_placeholders(ES.get(key, ""))
            provided_kwargs = set(call["kwargs"])
            
            # Marcadores que requiere la traducción pero que no se pasan en el código
            missing_kwargs = required_placeholders - provided_kwargs
            # Argumentos que se pasan en el código pero que no existen en la traducción
            extra_kwargs = provided_kwargs - required_placeholders
            
            if missing_kwargs or extra_kwargs:
                errors_found = True
                rel_path = os.path.relpath(call["filepath"], root_dir)
                print(f"[ERROR] Discrepancia de parámetros para get_text('{key}') en {rel_path} (Línea {call['line']}):")
                if missing_kwargs:
                    print(f"  - Faltan argumentos requeridos por la traducción: {sorted(list(missing_kwargs))}")
                if extra_kwargs:
                    print(f"  - Argumentos sobrantes no definidos en la traducción: {sorted(list(extra_kwargs))}")
                print("-" * 30)

    # 4. Advertencia de traducción no usada en el código (Clean Code)
    unused_keys = all_keys - used_keys
    # Filtrar posibles falsos positivos de llaves dinámicas comunes
    dynamic_prefixes = ["status_", "month_", "day_", "game_", "help_module_", "sim_"]
    filtered_unused = [
        k for k in unused_keys 
        if not any(k.startswith(p) for p in dynamic_prefixes)
    ]
    if filtered_unused:
        print(f"[WARNING] Se encontraron {len(filtered_unused)} llaves aparentemente no usadas en el código:")
        for k in sorted(filtered_unused)[:10]:
            print(f"  - {k}")
        if len(filtered_unused) > 10:
            print(f"  - ... y {len(filtered_unused) - 10} más.")
        print("-" * 30)

    if not errors_found:
        print("Perfecto! Todos los archivos de idioma estan 100% sincronizados y sin discrepancias de marcadores.")
        print(f"Total de llaves validadas: {len(all_keys)}")
        sys.exit(0)
    else:
        print("=" * 60)
        print("Se encontraron discrepancias en los archivos de idioma o llamadas del código.")
        sys.exit(1)

if __name__ == "__main__":
    validate_locales()
