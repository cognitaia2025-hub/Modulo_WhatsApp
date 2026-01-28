"""
Tests para el sistema de rate limiting.
"""

import time
import pytest
from src.middleware.rate_limiter import RateLimiter, rate_limit


class TestRateLimiter:
    """Tests para RateLimiter"""

    def test_rate_limiter_allows_within_limit(self):
        """Test: Permite llamadas dentro del límite"""
        limiter = RateLimiter(calls=5, period=1)  # 5 llamadas por segundo

        # Debe permitir 5 llamadas
        for i in range(5):
            assert limiter.acquire() is True

    def test_rate_limiter_blocks_exceeding_limit(self):
        """Test: Bloquea llamadas que exceden el límite"""
        limiter = RateLimiter(calls=3, period=1)

        # Primeras 3 deben pasar
        for i in range(3):
            assert limiter.acquire() is True

        # La 4ta debe bloquearse
        assert limiter.acquire() is False

    def test_rate_limiter_resets_after_period(self):
        """Test: Se resetea después del período"""
        limiter = RateLimiter(calls=2, period=1)  # 2 llamadas por segundo

        # Primeras 2 pasan
        assert limiter.acquire() is True
        assert limiter.acquire() is True

        # 3ra se bloquea
        assert limiter.acquire() is False

        # Esperar 1 segundo
        time.sleep(1.1)

        # Ahora debe permitir de nuevo
        assert limiter.acquire() is True

    def test_rate_limit_decorator(self):
        """Test: Decorator funciona correctamente"""
        call_count = 0

        @rate_limit("google_calendar")
        def test_function():
            nonlocal call_count
            call_count += 1
            return "success"

        # Llamar varias veces
        for i in range(5):
            result = test_function()
            assert result == "success"

        # Debe haber ejecutado 5 veces
        assert call_count == 5

    def test_concurrent_calls_respect_limit(self):
        """Test: Llamadas concurrentes respetan el límite"""
        import threading

        limiter = RateLimiter(calls=10, period=1)
        success_count = 0
        lock = threading.Lock()

        def make_call():
            nonlocal success_count
            if limiter.acquire():
                with lock:
                    success_count += 1

        # Crear 20 threads simultáneos
        threads = []
        for i in range(20):
            t = threading.Thread(target=make_call)
            threads.append(t)
            t.start()

        # Esperar a que terminen
        for t in threads:
            t.join()

        # Solo 10 deben haber tenido éxito (el límite)
        assert success_count == 10
