# Archivo: services/math_service.py

def calcular(operacion: str, a: int, b: int) -> float:
    """Centraliza la lógica matemática."""
    if operacion == "sumar":
        return a + b
    elif operacion == "restar":
        return a - b
    elif operacion == "multiplicacion":
        return a * b
    elif operacion == "division":
        if b == 0:
            raise ValueError("No se puede dividir por cero.")
        return round(a / b, 2)
    else:
        raise ValueError("Operación no válida.")