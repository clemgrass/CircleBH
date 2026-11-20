"""El polígono regular: sus vértices, sus aristas y los sectores que las ordenan (ADR 0020).

El vértice `k` está en el ángulo `π/2 + 2πk / sides`: el primero apunta hacia arriba, y
los demás siguen en sentido antihorario (ADR 0003). La arista `k` va del vértice `k` al
`k + 1`, y la última cierra en el vértice 0.

Salvo `regular_polygon`, todo se mide desde el centro del polígono.
"""

import math
from collections.abc import Iterable

from pygame.math import Vector2

from circlebh.world.collisions import crossing

TIE = 1e-9
"""Dos cruces cuyos `t` difieren menos que esto empatan, y gana la arista de índice
menor. Cubre el redondeo de `t` cuando una bala pasa por un vértice.

Límite: no cubre el redondeo de `u` en `crossing`. Si el tramo pasa a ~1e-15 de un
vértice, ese redondeo puede descartar una de las dos aristas, y gana la otra o, rara
vez, ninguna en ese vértice. En el juego no se nota: exige pasar a esa distancia."""

ENVELOPE_SLACK = 1e-9
"""Margen del círculo envolvente, en unidades del plano. Por redondeo, un vértice puede
quedar a `radius + 4e-15` del centro, y una envolvente justa descartaría un golpe en él.
Un margen es siempre seguro: solo hace probar las líneas en algún caso de más."""

NEAR_HALF_TURN = 1e-6
"""Si el barrido de un tramo queda a menos de esto de media vuelta, el tramo pasa por el
centro o muy cerca, y el sentido del barrido no es confiable: se revisan todas."""


def vertex(radius: float, sides: int, k: int) -> Vector2:
    """El vértice `k`, en el ángulo `π/2 + 2πk / sides`."""
    angle = math.pi / 2 + math.tau * k / sides
    return radius * Vector2(math.cos(angle), math.sin(angle))


def regular_polygon(center: Vector2, radius: float, sides: int) -> list[Vector2]:
    """Los vértices de un polígono regular inscrito en el círculo de `radius`."""
    return [center + vertex(radius, sides, k) for k in range(sides)]


def polygon_edge(radius: float, sides: int, k: int) -> tuple[Vector2, Vector2]:
    """La arista `k`, del vértice `k` al `k + 1`."""
    return vertex(radius, sides, k), vertex(radius, sides, (k + 1) % sides)


def sector(point: Vector2, sides: int) -> int:
    """El sector donde cae `point`: `⌊((θ − π/2) mod 2π) · sides / 2π⌋`.

    El sector `k` va del vértice `k` al `k + 1`, así que contiene entera a la arista `k`.
    """
    angle = math.atan2(point.y, point.x)
    return math.floor((angle - math.pi / 2) % math.tau * sides / math.tau) % sides


def edge_sectors(start: Vector2, end: Vector2, sides: int) -> list[int]:
    """Las aristas que el tramo `start→end` podría cruzar.

    A lo largo de un tramo que no pasa por el centro, el ángulo cambia en un solo sentido
    y barre menos de media vuelta. Una arista que el tramo cruza está en un sector de ese
    barrido, así que basta recorrer los sectores de `start` a `end` por el camino corto.
    Se suma uno a cada lado, por si el redondeo deja un extremo en el sector vecino. Si un
    extremo está en el centro, o el barrido es de casi media vuelta, devuelve todas.

    Ese sector de más a cada lado y `NEAR_HALF_TURN` son defensivos: la revisión de #25
    probó 200.000 tramos adversariales sin ellos y no encontró un caso que los necesite.
    """
    if start.length_squared() == 0 or end.length_squared() == 0:
        return list(range(sides))
    a0 = math.atan2(start.y, start.x)
    a1 = math.atan2(end.y, end.x)
    # El barrido corto, en [−π, π).
    sweep = (a1 - a0 + math.pi) % math.tau - math.pi
    if abs(sweep) > math.pi - NEAR_HALF_TURN:
        return list(range(sides))
    direction = 1 if sweep >= 0 else -1
    first, last = sector(start, sides), sector(end, sides)
    found = {(first - direction) % sides}
    k = first
    while True:
        found.add(k)
        if k == last or len(found) >= sides:
            break
        k = (k + direction) % sides
    found.add((last + direction) % sides)
    return sorted(found)


def first_hit(
    start: Vector2, end: Vector2, radius: float, sides: int, edges: Iterable[int]
) -> tuple[float, int] | None:
    """La primera arista de `edges` que cruza el tramo `start→end`, como `(t, k)`.

    `t` es la fracción del tramo donde la cruza. Si dos empatan (ver `TIE`), gana la de
    índice menor.
    """
    best: tuple[float, int] | None = None
    for k in sorted(edges):
        a, b = polygon_edge(radius, sides, k)
        t = crossing(start, end, a, b)
        if t is not None and (best is None or t < best[0] - TIE):
            best = (t, k)
    return best
