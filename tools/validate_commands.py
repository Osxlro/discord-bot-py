import os
import sys
import ast
import re

COMMAND_NAME_REGEX = re.compile(r"^[a-z0-9_-]{1,32}$")

def is_slash_or_hybrid(decorator):
    if isinstance(decorator, ast.Call):
        func = decorator.func
    else:
        func = decorator
        
    if isinstance(func, ast.Attribute):
        attr_name = func.attr
        value_name = ""
        if isinstance(func.value, ast.Name):
            value_name = func.value.id
        full_name = f"{value_name}.{attr_name}"
        if full_name in {"commands.hybrid_command", "commands.hybrid_group", "app_commands.command"}:
            return True
        if attr_name in {"command", "group"}:
            return True
    return False

def is_prefix_command(decorator):
    if isinstance(decorator, ast.Call):
        func = decorator.func
    else:
        func = decorator
        
    if isinstance(func, ast.Attribute):
        attr_name = func.attr
        value_name = ""
        if isinstance(func.value, ast.Name):
            value_name = func.value.id
        full_name = f"{value_name}.{attr_name}"
        if full_name == "commands.command":
            return True
    return False

def get_decorator_args(decorator):
    name = None
    description = None
    if isinstance(decorator, ast.Call):
        for kw in decorator.keywords:
            if kw.arg == "name" and isinstance(kw.value, ast.Constant):
                name = kw.value.value
            elif kw.arg == "description" and isinstance(kw.value, ast.Constant):
                description = kw.value.value
    return name, description

def analyze_file(filename):
    with open(filename, "r", encoding="utf-8") as f:
        source = f.read()
    
    try:
        tree = ast.parse(source, filename=filename)
    except SyntaxError as e:
        return [(e.lineno or 0, f"Error de Sintaxis: {e.msg}")], []
        
    errors = []
    commands_found = []
    has_setup = False
    has_cog = False
    
    for stmt in tree.body:
        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)) and stmt.name == "setup":
            has_setup = True
            
        elif isinstance(stmt, ast.ClassDef):
            is_cog = False
            for base in stmt.bases:
                if isinstance(base, ast.Attribute) and base.attr == "Cog":
                    if isinstance(base.value, ast.Name) and base.value.id == "commands":
                        is_cog = True
            if is_cog:
                has_cog = True
                
            for class_stmt in stmt.body:
                if isinstance(class_stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    for decorator in class_stmt.decorator_list:
                        is_slash = is_slash_or_hybrid(decorator)
                        is_pref = is_prefix_command(decorator)
                        
                        if is_slash or is_pref:
                            is_subcommand = False
                            parent_group = None
                            
                            if isinstance(decorator, ast.Call):
                                func = decorator.func
                            else:
                                func = decorator
                                
                            if isinstance(func, ast.Attribute) and func.attr in {"command", "group"}:
                                if isinstance(func.value, ast.Name) and func.value.id != "commands":
                                    is_subcommand = True
                                    parent_group = func.value.id
                                    
                            dec_name, dec_desc = get_decorator_args(decorator)
                            cmd_name = dec_name or class_stmt.name
                            
                            docstring = ast.get_docstring(class_stmt)
                            doc_desc = docstring.strip().split('\n')[0] if docstring else ""
                            cmd_desc = dec_desc or doc_desc or ""
                            
                            cmd_type = "hybrid" if is_slash else "prefix"
                            commands_found.append({
                                "name": cmd_name,
                                "type": cmd_type,
                                "line": class_stmt.lineno,
                                "description": cmd_desc,
                                "is_slash": is_slash,
                                "is_subcommand": is_subcommand,
                                "parent_group": parent_group
                            })
                            
                            # Validate Name
                            if is_slash:
                                if not COMMAND_NAME_REGEX.match(cmd_name):
                                    errors.append((class_stmt.lineno, f"El comando slash/híbrido '{cmd_name}' tiene un nombre inválido. Debe ser minúscula, alfanumérico, sin espacios, y tener entre 1 y 32 caracteres (regex: ^[a-z0-9_-]{{1,32}}$)."))
                            else:
                                if " " in cmd_name:
                                    errors.append((class_stmt.lineno, f"El comando prefijo '{cmd_name}' no puede contener espacios en su nombre."))
                                    
                            # Validate Description
                            if is_slash:
                                if not cmd_desc.strip():
                                    errors.append((class_stmt.lineno, f"El comando slash/híbrido '{cmd_name}' no tiene descripción. Debe especificarse en el decorador o en el docstring de la función."))
                                elif len(cmd_desc) > 100:
                                    errors.append((class_stmt.lineno, f"La descripción del comando slash/híbrido '{cmd_name}' excede los 100 caracteres permitidos por Discord (Largo actual: {len(cmd_desc)})."))
                                    
                            # Validate Parameters/Arguments for Discord Slash Commands
                            if is_slash:
                                # Omit first two args (self, ctx/interaction)
                                cmd_args = class_stmt.args.args[2:]
                                for arg in cmd_args:
                                    arg_name = arg.arg
                                    if not COMMAND_NAME_REGEX.match(arg_name):
                                        errors.append((class_stmt.lineno, f"[ERROR] El parámetro '{arg_name}' del comando slash/híbrido '{cmd_name}' tiene un nombre inválido. Debe ser minúscula, alfanumérico, sin espacios, y tener entre 1 y 32 caracteres (regex: ^[a-z0-9_-]{{1,32}}$)."))
                                    
    if has_cog and not has_setup:
        errors.append((0, f"El archivo contiene un Cog pero le falta la función global 'setup(bot)' para registrarlo."))
        
    return errors, commands_found

def run_validation():
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    commands_dir = os.path.join(root_dir, "cogs", "commands")
    if not os.path.exists(commands_dir):
        print(f"Error: No se encontró el directorio {commands_dir}")
        sys.exit(1)
        
    # Búsqueda recursiva
    files = []
    for r, _, f_list in os.walk(commands_dir):
        for f in f_list:
            if f.endswith(".py"):
                files.append(os.path.join(r, f))
                
    files = sorted(files)
    
    errors_by_file = {}
    top_level_commands = {}
    group_subcommands = {}
    
    print("\n[Command Validator] Iniciando comprobacion de comandos y Cogs...")
    print("=" * 60)
    
    for filename in files:
        errors, cmds = analyze_file(filename)
        
        for cmd in cmds:
            name = cmd["name"]
            if cmd["is_subcommand"]:
                group = cmd["parent_group"]
                if group not in group_subcommands:
                    group_subcommands[group] = {}
                if name in group_subcommands[group]:
                    prev = group_subcommands[group][name]
                    errors.append((cmd["line"], f"Colisión de subcomandos: El subcomando '{name}' del grupo '{group}' ya está definido en '{prev['file']}' (línea {prev['line']})."))
                else:
                    group_subcommands[group][name] = {"file": filename, "line": cmd["line"]}
            else:
                if name in top_level_commands:
                    prev = top_level_commands[name]
                    errors.append((cmd["line"], f"Colisión de comandos: El comando '{name}' ya está definido en '{prev['file']}' (línea {prev['line']})."))
                else:
                    top_level_commands[name] = {"file": filename, "line": cmd["line"]}
                    
        if errors:
            errors_by_file[filename] = errors
            
    if errors_by_file:
        print("\nSe encontraron los siguientes problemas en los comandos:")
        print("=" * 60)
        for filename, errors in errors_by_file.items():
            relative_path = os.path.relpath(filename, root_dir)
            print(f"\n[File] Archivo: {relative_path}")
            for line, msg in errors:
                print(f"  - Linea {line}: {msg}")
        print("\n" + "=" * 60)
        sys.exit(1)
    else:
        total_commands = len(top_level_commands) + sum(len(sub) for sub in group_subcommands.values())
        print("=" * 60)
        print(f"Perfecto! Todos los comandos pasaron la validación de Discord con éxito.")
        print(f"Total de comandos validados: {total_commands} ({len(top_level_commands)} principales, {total_commands - len(top_level_commands)} subcomandos).")
        sys.exit(0)

if __name__ == "__main__":
    run_validation()
