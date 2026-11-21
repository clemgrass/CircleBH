"""El ritmo: los patrones euclidianos y la grilla de semicorcheas (ADR 0022).

La música avanza por semicorcheas. Cada una es un bloque de audio, y un compás tiene 16.
"""

from dataclasses import dataclass

RATE = 44100
"""Muestras por segundo."""
SIXTEENTHS = 16
"""Semicorcheas por compás."""
SWING = 0.56
"""Qué parte del par de semicorcheas ocupa la primera: con 0,5 no hay swing."""


def euclid(k: int, n: int) -> list[bool]:
    """E(k, n): k golpes repartidos lo más parejo posible en n pasos (Toussaint 2005).

    El paso `i` es golpe si `(i·k) mod n < k`: el golpe cae cada vez que `i·k/n` cruza
    un entero, como una recta de pendiente `k/n` dibujada en una grilla. El primer
    golpe está en el paso 0. E(3, 8) es el tresillo: `x . . x . . x .`.
    """
    if not 0 < k <= n:
        raise ValueError(f"E(k, n) pide 0 < k ≤ n, llegó k={k}, n={n}")
    return [(i * k) % n < k for i in range(n)]


@dataclass(frozen=True)
class Grid:
    """Dónde empieza cada semicorchea, en muestras, con el tempo del tema (ADR 0025)."""

    bpm: float

    @property
    def samples(self) -> float:
        """Muestras por semicorchea. No es entero: cada inicio se redondea por separado,
        así que el error no se acumula."""
        return RATE * 60 / self.bpm / 4

    @property
    def bar_seconds(self) -> float:
        """Cuánto dura un compás, en segundos."""
        return SIXTEENTHS * self.samples / RATE

    def start(self, g: int) -> int:
        """La muestra donde empieza la semicorchea `g`."""
        return round(g * self.samples)

    def swing(self, g: int) -> int:
        """Cuántas muestras se atrasa lo que suena en la semicorchea `g`: solo las
        impares, y lo que les falta para ocupar `SWING` del par."""
        return round((SWING - 0.5) * 2 * self.samples) if g % 2 else 0
