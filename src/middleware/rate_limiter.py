"""
Middleware de rate limiting para APIs externas.
Previene exceder límites de llamadas a servicios externos.
"""

import time
import asyncio
import threading
from functools import wraps
from typing import Callable, Dict
from collections import deque
from datetime import datetime, timedelta


class RateLimiter:
    """Rate limiter con ventana deslizante"""

    def __init__(self, calls: int, period: int):
        """
        Args:
            calls: Número máximo de llamadas
            period: Período en segundos
        """
        self.calls = calls
        self.period = period
        self.timestamps: deque = deque()
        self.lock = threading.Lock()

    def _clean_old_timestamps(self):
        """Eliminar timestamps fuera de la ventana de tiempo"""
        now = datetime.now()
        cutoff = now - timedelta(seconds=self.period)

        while self.timestamps and self.timestamps[0] < cutoff:
            self.timestamps.popleft()

    def acquire(self) -> bool:
        """
        Intentar adquirir permiso para ejecutar.
        Retorna True si se puede ejecutar, False si debe esperar.
        """
        with self.lock:
            self._clean_old_timestamps()

            if len(self.timestamps) < self.calls:
                self.timestamps.append(datetime.now())
                return True

            return False

    def wait_if_needed(self):
        """Esperar si es necesario para respetar el rate limit"""
        while not self.acquire():
            time.sleep(0.1)  # Esperar 100ms y reintentar


# Rate limiters globales para cada API
RATE_LIMITERS: Dict[str, RateLimiter] = {
    "google_calendar": RateLimiter(calls=10, period=1),  # 10 req/seg
    "deepseek": RateLimiter(calls=20, period=60),  # 20 req/min
    "anthropic": RateLimiter(calls=15, period=60),  # 15 req/min
    "whatsapp": RateLimiter(calls=80, period=1),  # 80 req/seg
}


def rate_limit(api_name: str):
    """
    Decorador para aplicar rate limiting a una función.

    Args:
        api_name: Nombre del API ('google_calendar', 'deepseek', etc.)

    Usage:
        @rate_limit('google_calendar')
        def call_google_api():
            ...
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            limiter = RATE_LIMITERS.get(api_name)

            if limiter:
                limiter.wait_if_needed()

            return func(*args, **kwargs)

        return wrapper

    return decorator


# Versión asíncrona (para uso con asyncio)
def async_rate_limit(api_name: str):
    """
    Decorador para aplicar rate limiting a funciones async.

    Usage:
        @async_rate_limit('deepseek')
        async def call_deepseek_api():
            ...
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            limiter = RATE_LIMITERS.get(api_name)

            if limiter:
                # Esperar de forma asíncrona
                while not limiter.acquire():
                    await asyncio.sleep(0.1)

            return await func(*args, **kwargs)

        return wrapper

    return decorator
