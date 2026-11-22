"""Las figuras de los enemigos: el polígono estrellado `{n/s}` (spec de la 0.2.0).

Los `n` vértices son los del polígono regular (`polygon.py`): el vértice `k` está en
`π/2 + 2πk/n`. Cada salto `s` une el vértice `k` con el `k + s`, y la línea de índice
`j·n + k` es la de `k` con el salto `steps[j]`. Con `steps = (1,)`, la línea `k` es la
arista `k` del polígono regular, así que los sectores del ADR 0020 siguen valiendo.

Todo se mide desde el centro de la figura, sin girar.
"""

from pygame.math import Vector2

from circlebh.balance import StarPolygonShape
from circlebh.world.polygon import vertex


def line_vertices(shape: StarPolygonShape) -> list[tuple[int, int]]:
    """Los vértices que une cada línea, en el orden de sus índices."""
    n = shape.vertices
    return [(k, (k + s) % n) for s in shape.steps for k in range(n)]


def local_lines(
    shape: StarPolygonShape, radius: float
) -> list[tuple[Vector2, Vector2]]:
    """Las líneas de la figura entera, en el círculo de `radius`."""
    n = shape.vertices
    return [
        (vertex(radius, n, a), vertex(radius, n, b)) for a, b in line_vertices(shape)
    ]


def check_shape(shape: StarPolygonShape, where: str) -> None:
    """Rechaza una figura cuyas líneas se repetirían o que no encierra nada.

    Con `s ≥ n/2`, el salto `s` da las mismas líneas que `n − s`, y con `s = n/2` cada
    línea sale dos veces. `where` nombra al enemigo en el mensaje."""
    n, steps = shape.vertices, shape.steps
    if n < 3:
        raise ValueError(f"{where}.shape.vertices: necesita al menos 3, no {n}")
    if not steps or len(set(steps)) != len(steps):
        raise ValueError(f"{where}.shape.steps: necesita saltos distintos, no {steps}")
    for s in steps:
        if not 1 <= s < n / 2:
            raise ValueError(
                f"{where}.shape.steps: cada salto cumple 1 ≤ s < {n}/2, y {s} no"
            )
