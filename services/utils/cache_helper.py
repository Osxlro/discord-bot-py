import time
from typing import Any, Dict, Optional, Tuple

class SimpleTTLCache:
    """
    Caché en memoria con límite de tamaño (evicción FIFO) y expiración por tiempo (TTL).
    Previene fugas de memoria en ejecuciones prolongadas del bot.
    """
    def __init__(self, max_size: int = 100, ttl: float = 86400) -> None:
        """
        Args:
            max_size: Cantidad máxima de elementos en caché.
            ttl: Tiempo de vida en segundos para cada elemento.
        """
        self.max_size: int = max_size
        self.ttl: float = ttl
        self._cache: Dict[Any, Tuple[float, Any]] = {}

    def get(self, key: Any) -> Optional[Any]:
        """Obtiene un elemento de la caché si no ha expirado."""
        if key in self._cache:
            timestamp, value = self._cache[key]
            if time.time() - timestamp < self.ttl:
                return value
            # Eliminar si ha expirado
            self._cache.pop(key, None)
        return None

    def set(self, key: Any, value: Any) -> None:
        """Almacena un elemento en la caché aplicando políticas de desalojo."""
        now_real = time.time()
        
        # Si excedemos el tamaño máximo, hacemos limpieza de expirados primero
        if len(self._cache) >= self.max_size:
            expired_keys = [k for k, (t, _) in self._cache.items() if now_real - t >= self.ttl]
            for k in expired_keys:
                self._cache.pop(k, None)

            # Si sigue excediendo, removemos el elemento más antiguo (FIFO)
            if len(self._cache) >= self.max_size:
                first_key = next(iter(self._cache))
                self._cache.pop(first_key, None)

        self._cache[key] = (now_real, value)

    def clear(self) -> None:
        """Limpia todos los elementos de la caché."""
        self._cache.clear()
