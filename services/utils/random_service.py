import random
from config import settings

def obtener_cara_cruz() -> tuple[str, str]:
    """Retorna una tupla (Texto, URL_GIF)."""
    # Usamos los enlaces directos de CDN para asegurar que carguen siempre
    opciones = [
        ("SOL", settings.ASSETS["COINFLIP_HEADS"]), 
        ("LUNA", settings.ASSETS["COINFLIP_TAILS"])
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