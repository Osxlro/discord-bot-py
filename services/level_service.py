import math

def calcular_xp_necesaria(nivel_actual: int) -> int:
    """Fórmula RPG estándar para calcular la XP necesaria para el siguiente nivel."""
    # Ejemplo: Nivel 1 -> 100 XP, Nivel 2 -> 155 XP, etc.
    return 100 + (50 * nivel_actual)

def calcular_nivel(xp_total: int) -> int:
    """Calcula el nivel basado en la XP total (función inversa aproximada)."""
    # Esta es una simplificación, para sistemas complejos es mejor guardar el nivel en DB
    # Pero para empezar, usaremos el nivel guardado en DB directamente.
    return 0