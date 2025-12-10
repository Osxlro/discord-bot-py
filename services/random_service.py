import random

def obtener_cara_cruz() -> tuple[str, str]:
    """Retorna una tupla (Texto, Emoji)."""
    opciones = [
        ("Cara", "🪙"), 
        ("Cruz", "🦅")
    ]
    return random.choice(opciones)

def elegir_opcion(opcion_a: str, opcion_b: str) -> str:
    """Elige una de las dos opciones."""
    return random.choice([opcion_a, opcion_b])