import random

def obtener_cara_cruz() -> tuple[str, str]:
    """Retorna una tupla (Texto, Emoji)."""
    opciones = [
        ("SOL", "🪙"), 
        ("LUNA", "🦅")
    ]
    return random.choice(opciones)

def elegir_opcion(opcion_a: str, opcion_b: str) -> str:
    """Elige una de las dos opciones."""
    return random.choice([opcion_a, opcion_b])

# --- NUEVA FUNCIÓN ---
def verificar_suerte(probabilidad: float) -> bool:
    """
    Retorna True si se cumple la probabilidad dada.
    :param probabilidad: Float entre 0.0 y 1.0 (Ej: 0.01 es 1%)
    """
    if probabilidad <= 0: return False
    if probabilidad >= 1: return True
    return random.random() < probabilidad