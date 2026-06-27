import os
import sys
import ast
import re

# Set project root to sys.path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(root_dir)

BASELINE_COLUMNS = {
    "users": {
        "user_id", "birthday", "celebrate", "custom_prefix", 
        "description", "personal_level_msg", "personal_birthday_msg", "bank_coins"
    },
    "guild_stats": {
        "guild_id", "user_id", "xp", "level"
    },
    "guild_config": {
        "guild_id", "chaos_enabled", "chaos_probability", "welcome_channel_id", 
        "confessions_channel_id", "logs_channel_id", "birthday_channel_id", 
        "autorole_id", "mention_response", "server_level_msg", "server_birthday_msg", 
        "server_kick_msg", "server_ban_msg"
    },
    "bot_persistence": {
        "namespace", "key", "data"
    },
    "bot_statuses": {
        "id", "type", "text"
    },
    "warns": {
        "id", "guild_id", "user_id", "mod_id", "reason", "timestamp"
    },
    "user_inventory": {
        "user_id", "item_id", "quantity"
    },
    "shop_items": {
        "item_id", "emoji", "cost", "availability", "start_date", "end_date",
        "purchase_limit", "total_stock", "name_default", "desc_default", "category",
        "names_json", "descs_json"
    }
}

class DbServiceVisitor(ast.NodeVisitor):
    def __init__(self):
        self.required_tables = set()
        self.create_table_queries = []
        self.ensure_column_calls = []

    def visit_Assign(self, node):
        # Detect REQUIRED_TABLES
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == "REQUIRED_TABLES":
                if isinstance(node.value, ast.Set):
                    for elt in node.value.elts:
                        if isinstance(elt, ast.Constant):
                            self.required_tables.add(elt.value)
                        elif isinstance(elt, ast.Str): # Support Python < 3.8
                            self.required_tables.add(elt.s)
        self.generic_visit(node)

    def visit_Call(self, node):
        # Detect execute("CREATE TABLE IF NOT EXISTS ...")
        is_execute = False
        if isinstance(node.func, ast.Name) and node.func.id == "execute":
            is_execute = True
        elif isinstance(node.func, ast.Attribute) and node.func.attr == "execute":
            is_execute = True

        if is_execute and node.args:
            first_arg = node.args[0]
            query_str = None
            if isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str):
                query_str = first_arg.value
            elif isinstance(first_arg, ast.Str):
                query_str = first_arg.s
            
            if query_str and "CREATE TABLE" in query_str:
                self.create_table_queries.append((node.lineno, query_str))

        # Detect _ensure_column("table", "column", "def")
        is_ensure = False
        if isinstance(node.func, ast.Name) and node.func.id == "_ensure_column":
            is_ensure = True
        elif isinstance(node.func, ast.Attribute) and node.func.attr == "_ensure_column":
            is_ensure = True

        if is_ensure and len(node.args) >= 2:
            arg_table = node.args[0]
            arg_col = node.args[1]
            table_val = None
            col_val = None

            if isinstance(arg_table, ast.Constant):
                table_val = arg_table.value
            elif isinstance(arg_table, ast.Str):
                table_val = arg_table.s

            if isinstance(arg_col, ast.Constant):
                col_val = arg_col.value
            elif isinstance(arg_col, ast.Str):
                col_val = arg_col.s

            if table_val and col_val:
                self.ensure_column_calls.append((node.lineno, table_val, col_val))

        self.generic_visit(node)

def parse_columns_from_query(query):
    # Extract text inside the first outer parenthesis
    start = query.find("(")
    end = query.rfind(")")
    if start == -1 or end == -1:
        return set()
    
    inside = query[start+1:end]
    
    # Simple parser that handles comma separation ignoring nested parenthesis
    columns = set()
    paren_depth = 0
    current_token = []
    
    for char in inside:
        if char == "(":
            paren_depth += 1
            current_token.append(char)
        elif char == ")":
            paren_depth -= 1
            current_token.append(char)
        elif char == "," and paren_depth == 0:
            line = "".join(current_token).strip()
            if line:
                # First word is generally the column name (excluding keywords like PRIMARY KEY, FOREIGN KEY, etc.)
                words = line.split()
                if words and words[0].upper() not in {"PRIMARY", "FOREIGN", "CONSTRAINT", "UNIQUE", "CHECK"}:
                    columns.add(words[0].lower().strip("`\"'"))
            current_token = []
        else:
            current_token.append(char)
            
    # Add last token
    line = "".join(current_token).strip()
    if line:
        words = line.split()
        if words and words[0].upper() not in {"PRIMARY", "FOREIGN", "CONSTRAINT", "UNIQUE", "CHECK"}:
            columns.add(words[0].lower().strip("`\"'"))
            
    return columns

def validate_db_schema():
    db_service_path = os.path.join(root_dir, "services", "core", "db_service.py")
    if not os.path.exists(db_service_path):
        print(f"Error: No se encontró db_service.py en {db_service_path}")
        sys.exit(1)

    print("\n[DB Schema Validator] Iniciando comprobacion de consistencia del esquema...")
    print("=" * 60)

    try:
        with open(db_service_path, "r", encoding="utf-8") as f:
            source = f.read()
        tree = ast.parse(source, filename=db_service_path)
    except Exception as e:
        print(f"[ERROR] Error al parsear db_service.py: {e}")
        sys.exit(1)

    visitor = DbServiceVisitor()
    visitor.visit(tree)

    errors_found = False

    # 1. Validate REQUIRED_TABLES
    print(f"REQUIRED_TABLES encontradas: {visitor.required_tables}")
    
    created_tables = {}
    table_regex = re.compile(r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(\w+)", re.IGNORECASE)
    
    for line, query in visitor.create_table_queries:
        match = table_regex.search(query)
        if match:
            table_name = match.group(1).lower()
            created_tables[table_name] = (line, query)
            
            # Check if it is listed in REQUIRED_TABLES
            if table_name not in visitor.required_tables:
                errors_found = True
                print(f"[ERROR] Tabla '{table_name}' definida en CREATE TABLE (Línea {line}) pero falta en REQUIRED_TABLES.")
        else:
            print(f"[WARNING] No se pudo extraer el nombre de la tabla de la consulta en la Línea {line}")

    # 2. Check migrations (_ensure_column) for non-baseline columns
    ensure_map = {}
    for line, table, col in visitor.ensure_column_calls:
        table_l = table.lower()
        col_l = col.lower()
        if table_l not in ensure_map:
            ensure_map[table_l] = set()
        ensure_map[table_l].add(col_l)

    for table_name, (line, query) in created_tables.items():
        columns = parse_columns_from_query(query)
        baseline = BASELINE_COLUMNS.get(table_name, set())
        
        non_baseline_cols = columns - baseline
        if non_baseline_cols:
            print(f"Tabla '{table_name}' (Línea {line}): Detectadas columnas no-base {non_baseline_cols}")
            for col in non_baseline_cols:
                # Verify that it has an _ensure_column call
                has_migration = False
                if table_name in ensure_map and col in ensure_map[table_name]:
                    has_migration = True
                    
                if not has_migration:
                    errors_found = True
                    print(f"[ERROR] Columna nueva '{col}' en la tabla '{table_name}' no tiene una llamada a _ensure_column() registrada en init_db().")
                    print(f"        Agrega: await _ensure_column(\"{table_name}\", \"{col}\", \"DEFINICIÓN_SQL\") para evitar errores en DBs existentes.")

    if not errors_found:
        print("Perfecto! El esquema de la base de datos y sus migraciones son consistentes.")
        sys.exit(0)
    else:
        print("=" * 60)
        print("Se encontraron inconsistencias en el esquema de base de datos o migraciones.")
        sys.exit(1)

if __name__ == "__main__":
    validate_db_schema()
