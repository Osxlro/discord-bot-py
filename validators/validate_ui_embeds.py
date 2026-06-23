import os
import sys
import ast

# Set project root to sys.path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(root_dir)

EXCEPTED_FILES = {
    # Estos archivos están exceptuados por requerir colores dinámicos (avatar, rol, fuente de audio)
    "profile_ui.py",
    "general_ui.py",
    "music_ui.py"
}

class EmbedInstantiationVisitor(ast.NodeVisitor):
    def __init__(self, filepath):
        self.filepath = filepath
        self.errors = []

    def visit_Call(self, node):
        is_embed_call = False
        
        # Caso 1: discord.Embed(...)
        if isinstance(node.func, ast.Attribute) and node.func.attr == "Embed":
            if isinstance(node.func.value, ast.Name) and node.func.value.id == "discord":
                is_embed_call = True
                
        # Caso 2: Embed(...) (si se importó 'from discord import Embed')
        elif isinstance(node.func, ast.Name) and node.func.id == "Embed":
            is_embed_call = True

        if is_embed_call:
            self.errors.append((node.lineno, node.col_offset))
            
        self.generic_visit(node)

def validate_ui_embeds():
    print("\n[UI Embeds Validator] Comprobando normativa de interfaces y embeds...")
    print("=" * 60)

    target_dirs = [
        os.path.join(root_dir, "cogs", "commands"),
        os.path.join(root_dir, "cogs", "tasks"),
        os.path.join(root_dir, "cogs", "events"),
        os.path.join(root_dir, "services", "features"),
        os.path.join(root_dir, "ui")
    ]


    files_to_check = []
    for directory in target_dirs:
        if not os.path.exists(directory):
            continue
        for r, _, files in os.walk(directory):
            for file in files:
                if file.endswith(".py"):
                    # Omitir archivos exceptuados
                    if file in EXCEPTED_FILES:
                        continue
                    files_to_check.append(os.path.join(r, file))

    errors_found = False

    for filepath in sorted(files_to_check):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                source = f.read()
            tree = ast.parse(source, filename=filepath)
            
            visitor = EmbedInstantiationVisitor(filepath)
            visitor.visit(tree)
            
            if visitor.errors:
                errors_found = True
                rel_path = os.path.relpath(filepath, root_dir)
                print(f"[ERROR] Archivo: {rel_path}")
                for line, col in visitor.errors:
                    print(f"  - Linea {line}, Col {col}: Se instanció 'discord.Embed' de forma directa.")
                    print(f"    Normativa: Está prohibido instanciar embeds directos en comandos o UI.")
                    print(f"    Usa los helpers de 'embed_service.py' (ej: embed_service.success, embed_service.error, etc.).")
                print("-" * 30)
        except Exception as e:
            print(f"[WARNING] No se pudo parsear {filepath}: {e}")

    if not errors_found:
        print("Perfecto! Todos los archivos de comandos y UI respetan la normativa de embeds.")
        sys.exit(0)
    else:
        print("=" * 60)
        print("Se encontraron violaciones a la normativa de embeds en los comandos o UI.")
        sys.exit(1)

if __name__ == "__main__":
    validate_ui_embeds()
