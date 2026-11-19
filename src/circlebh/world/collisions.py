"""Colisiones: cada cuerpo es un círculo (ADR 0006)."""

from pygame.math import Vector2


def circles_touch(a: Vector2, ra: float, b: Vector2, rb: float) -> bool:
    """Si el círculo de centro `a` y radio `ra` toca al de centro `b` y radio `rb`.

    Se tocan cuando la distancia entre los centros no pasa la suma de los radios.
    Tangentes cuenta como tocarse.
    """
    return a.distance_to(b) <= ra + rb
