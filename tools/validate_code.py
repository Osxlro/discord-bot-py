import os
import sys
import ast
import builtins

BUILTINS = set(dir(builtins))

class Scope:
    def __init__(self, parent=None, is_class=False):
        self.parent = parent
        self.is_class = is_class
        self.names = set()
        self.globals = set()
        self.nonlocals = set()

    def define(self, name):
        self.names.add(name)

    def is_defined(self, name):
        if name in self.names:
            return True
        if name in self.globals:
            return True
        if self.parent:
            if self.parent.is_class:
                return self.parent.parent.is_defined(name) if self.parent.parent else False
            return self.parent.is_defined(name)
        return False

def collect_names_from_target(target, defined):
    if isinstance(target, ast.Name):
        defined.add(target.id)
    elif isinstance(target, (ast.Tuple, ast.List)):
        for elt in target.elts:
            collect_names_from_target(elt, defined)
    elif isinstance(target, ast.Starred):
        collect_names_from_target(target.value, defined)

def collect_from_stmt(stmt, defined):
    if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        defined.add(stmt.name)
    elif isinstance(stmt, (ast.Import, ast.ImportFrom)):
        for alias in stmt.names:
            defined.add(alias.asname or alias.name.split('.')[0])
    elif isinstance(stmt, ast.Assign):
        for target in stmt.targets:
            collect_names_from_target(target, defined)
    elif isinstance(stmt, ast.AnnAssign):
        collect_names_from_target(stmt.target, defined)
    elif isinstance(stmt, (ast.For, ast.AsyncFor)):
        collect_names_from_target(stmt.target, defined)
        for s in stmt.body:
            collect_from_stmt(s, defined)
        for s in stmt.orelse:
            collect_from_stmt(s, defined)
    elif isinstance(stmt, (ast.With, ast.AsyncWith)):
        for item in stmt.items:
            if item.optional_vars:
                collect_names_from_target(item.optional_vars, defined)
        for s in stmt.body:
            collect_from_stmt(s, defined)
    elif isinstance(stmt, ast.Try):
        for s in stmt.body:
            collect_from_stmt(s, defined)
        for handler in stmt.handlers:
            if handler.name:
                defined.add(handler.name)
            for s in handler.body:
                collect_from_stmt(s, defined)
        for s in stmt.orelse:
            collect_from_stmt(s, defined)
        for s in stmt.finalbody:
            collect_from_stmt(s, defined)
    elif isinstance(stmt, ast.If):
        for s in stmt.body:
            collect_from_stmt(s, defined)
        for s in stmt.orelse:
            collect_from_stmt(s, defined)
    elif isinstance(stmt, ast.While):
        for s in stmt.body:
            collect_from_stmt(s, defined)
        for s in stmt.orelse:
            collect_from_stmt(s, defined)

def collect_definitions(node, is_function=False):
    defined = set()
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        for arg in node.args.args:
            defined.add(arg.arg)
        for arg in node.args.kwonlyargs:
            defined.add(arg.arg)
        if node.args.vararg:
            defined.add(node.args.vararg.arg)
        if node.args.kwarg:
            defined.add(node.args.kwarg.arg)
            
    body = node.body if hasattr(node, 'body') else []
    if isinstance(body, list):
        for stmt in body:
            collect_from_stmt(stmt, defined)
    return defined

class CodeValidator(ast.NodeVisitor):
    def __init__(self, filename, source_code):
        self.filename = filename
        self.source_code = source_code
        self.errors = []
        self.scopes = []

    def push_scope(self, scope):
        self.scopes.append(scope)

    def pop_scope(self):
        return self.scopes.pop()

    @property
    def current_scope(self):
        return self.scopes[-1] if self.scopes else None

    def visit_Module(self, node):
        global_scope = Scope(parent=None)
        for name in BUILTINS:
            global_scope.define(name)
        for name in {"__file__", "__name__", "__package__", "__doc__", "__path__", "__loader__", "__spec__"}:
            global_scope.define(name)
            
        defs = collect_definitions(node)
        for d in defs:
            global_scope.define(d)
            
        self.push_scope(global_scope)
        self.generic_visit(node)
        self.pop_scope()

    def visit_function(self, node):
        for decorator in node.decorator_list:
            self.visit(decorator)
        if node.returns:
            self.visit(node.returns)
        for default in node.args.defaults:
            self.visit(default)
        for default in node.args.kw_defaults:
            if default:
                self.visit(default)
        for arg in node.args.args:
            if arg.annotation:
                self.visit(arg.annotation)
        for arg in node.args.kwonlyargs:
            if arg.annotation:
                self.visit(arg.annotation)
        if node.args.vararg and node.args.vararg.annotation:
            self.visit(node.args.vararg.annotation)
        if node.args.kwarg and node.args.kwarg.annotation:
            self.visit(node.args.kwarg.annotation)

        func_scope = Scope(parent=self.current_scope)
        defs = collect_definitions(node, is_function=True)
        for d in defs:
            func_scope.define(d)
            
        for stmt in ast.walk(node):
            if isinstance(stmt, ast.Global):
                for name in stmt.names:
                    func_scope.globals.add(name)
            elif isinstance(stmt, ast.Nonlocal):
                for name in stmt.names:
                    func_scope.nonlocals.add(name)

        self.push_scope(func_scope)
        for stmt in node.body:
            self.visit(stmt)
        self.pop_scope()

    def visit_FunctionDef(self, node):
        self.visit_function(node)

    def visit_AsyncFunctionDef(self, node):
        self.visit_function(node)

    def visit_ClassDef(self, node):
        for decorator in node.decorator_list:
            self.visit(decorator)
        for base in node.bases:
            self.visit(base)
        for kw in node.keywords:
            self.visit(kw)

        class_scope = Scope(parent=self.current_scope, is_class=True)
        defs = collect_definitions(node)
        for d in defs:
            class_scope.define(d)
            
        self.push_scope(class_scope)
        for stmt in node.body:
            self.visit(stmt)
        self.pop_scope()

    def visit_ListComp(self, node):
        self.visit_comp_node(node)

    def visit_SetComp(self, node):
        self.visit_comp_node(node)

    def visit_DictComp(self, node):
        self.visit_comp_node(node)

    def visit_GeneratorExp(self, node):
        self.visit_comp_node(node)

    def visit_comp_node(self, node):
        comp_scope = Scope(parent=self.current_scope)
        for gen in node.generators:
            collect_names_from_target(gen.target, comp_scope.names)
        self.push_scope(comp_scope)
        self.generic_visit(node)
        self.pop_scope()

    def visit_Lambda(self, node):
        lambda_scope = Scope(parent=self.current_scope)
        for arg in node.args.args:
            lambda_scope.define(arg.arg)
        for arg in node.args.kwonlyargs:
            lambda_scope.define(arg.arg)
        if node.args.vararg:
            lambda_scope.define(node.args.vararg.arg)
        if node.args.kwarg:
            lambda_scope.define(node.args.kwarg.arg)
            
        self.push_scope(lambda_scope)
        self.generic_visit(node)
        self.pop_scope()

    def visit_Name(self, node):
        if isinstance(node.ctx, ast.Load):
            name = node.id
            if not self.current_scope.is_defined(name):
                line = node.lineno
                col = node.col_offset
                self.errors.append((line, col, f"Variable indefinida: '{name}'"))
        self.generic_visit(node)

def run_validation():
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    target_dirs = ["cogs", "services", "ui", "config"]
    target_files = ["main.py"]
    
    files_to_check = []
    for directory in target_dirs:
        dir_path = os.path.join(root_dir, directory)
        if not os.path.exists(dir_path):
            continue
        for r, _, files in os.walk(dir_path):
            for file in files:
                if file.endswith(".py"):
                    files_to_check.append(os.path.join(r, file))
                    
    for file in target_files:
        file_path = os.path.join(root_dir, file)
        if os.path.exists(file_path):
            files_to_check.append(file_path)
            
    files_to_check = sorted(files_to_check)
    
    errors_by_file = {}
    checked_count = 0
    
    print("\n[Code Validator] Iniciando comprobacion de sintaxis y NameError...")
    print("=" * 60)
    
    for filename in files_to_check:
        checked_count += 1
        rel_path = os.path.relpath(filename, root_dir)
        print(f"[Code Validator] Verificando: {rel_path}...")
        try:
            with open(filename, "r", encoding="utf-8") as f:
                source = f.read()
            
            tree = ast.parse(source, filename=filename)
            
            validator = CodeValidator(filename, source)
            validator.visit(tree)
            
            if validator.errors:
                errors_by_file[filename] = validator.errors
                
        except SyntaxError as e:
            errors_by_file[filename] = [(e.lineno or 0, e.offset or 0, f"Error de Sintaxis: {e.msg}")]
        except Exception as e:
            errors_by_file[filename] = [(0, 0, f"Error inesperado al validar archivo: {e}")]
            
    if errors_by_file:
        print("\nSe encontraron los siguientes problemas de codigo:")
        print("=" * 60)
        for filename, errors in errors_by_file.items():
            # Mostramos ruta relativa al directorio raíz para mejor visualización
            relative_path = os.path.relpath(filename, root_dir)
            print(f"\n[File] Archivo: {relative_path}")
            for line, col, msg in errors:
                print(f"  - Linea {line}, Col {col}: {msg}")
        print("\n" + "=" * 60)
        print("Mantenimiento requerido. Se encontraron variables indefinidas o errores sintacticos.")
        sys.exit(1)
    else:
        print("=" * 60)
        print(f"Perfecto! Todos los {checked_count} archivos de codigo pasaron la validacion con exito.")
        sys.exit(0)

if __name__ == "__main__":
    run_validation()
