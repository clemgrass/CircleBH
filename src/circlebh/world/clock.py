"""Reloj de pasos fijos (ADR 0005).

La lógica del juego siempre avanza en pasos de `STEP` segundos, sin importar los FPS.
El tiempo real se acumula y se convierte en pasos; lo que sobra queda para el frame siguiente.
"""

from collections.abc import Iterable

STEP = 1 / 60
"""Duración de un paso de la lógica, en segundos."""

MAX_FRAME = 0.25
"""Tope del tiempo real de un frame: una pausa larga no hace correr cientos de pasos de golpe."""


class FixedStepClock:
    """Convierte el tiempo real de cada frame en una cantidad entera de pasos de `STEP`."""

    def __init__(self) -> None:
        self._accumulator = 0.0

    def advance(self, real_dt: float, speed: float = 1.0) -> int:
        """Suma `real_dt` segundos reales y devuelve cuántos pasos de `STEP` hay que dar ahora.

        Contrato:
        - `real_dt` se topa en `MAX_FRAME` y recién después se multiplica por `speed`:
          el tope es del tiempo real (ADR 0005), así que `--speed` no queda limitado por él.
        - Devuelve la cantidad de pasos completos que caben en el acumulador.
        - El resto (menos de un paso) queda guardado para la próxima llamada.
        """
        self._accumulator += min(real_dt, MAX_FRAME) * speed
        steps = 0
        while self._accumulator >= STEP:
            self._accumulator -= STEP
            steps += 1
        return steps


def capture_steps(times: Iterable[float]) -> list[int]:
    """Convierte tiempos en segundos al número del paso más cercano, en el mismo orden.

    Redondea en vez de truncar: 2,05 s son 123 pasos, pero `2.05 / STEP` da 122.99999999999999.
    """
    return [round(t / STEP) for t in times]
