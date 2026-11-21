"""La aparición: dónde nace lo que compra el director, y cuántos por paso (ADR 0025).

Todo se mide relativo al jugador. Una compra nace en el cuadrante con menos enemigos,
contando los vivos y los que esperan en la cola, y a `spawning.distance` o más, fuera
de la vista. Lo comprado entra a una cola, y sale de a `max_per_step` por paso.
"""

import math
import random
from collections import deque
from collections.abc import Iterable, Iterator, Sequence

from pygame.math import Vector2

from circlebh.balance import SpawningSpec
from circlebh.world.swarm import lattice

FORMATIONS = ("single", "ring", "line", "cluster")
"""Las formaciones que una sección puede usar (`SectionSpec.formations`)."""

QUARTER = math.pi / 2


def check_spawning(spec: SpawningSpec) -> None:
    """Rechaza números de aparición que no tienen sentido, nombrando el campo."""
    low, high = spec.formation_size
    if not 1 <= low <= high:
        raise ValueError(
            f"spawning.formation_size: necesita 1 ≤ menor ≤ mayor, y es {low, high}"
        )
    if spec.max_per_step < 1:
        raise ValueError("spawning.max_per_step: tiene que ser al menos 1")
    if spec.formation_gap < 0:
        raise ValueError("spawning.formation_gap: no puede ser negativo")


def quadrant(offset: Vector2) -> int:
    """El cuadrante de `offset`, de 0 a 3, antihorario desde +x.

    Un punto sobre un eje va al cuadrante que empieza en ese eje, y el origen, al 0. Se
    decide por los signos, sin ángulos, para que un eje no caiga a un lado u otro por
    el redondeo.
    """
    x, y = offset
    if x > 0 and y >= 0:
        return 0
    if x <= 0 and y > 0:
        return 1
    if x < 0 and y <= 0:
        return 2
    if x >= 0 and y < 0:
        return 3
    return 0


def emptiest_quadrants(offsets: Iterable[Vector2]) -> list[int]:
    """Los cuadrantes con menos puntos de `offsets`, de menor a mayor."""
    counts = [0, 0, 0, 0]
    for offset in offsets:
        counts[quadrant(offset)] += 1
    least = min(counts)
    return [q for q in range(4) if counts[q] == least]


def _shape(kind: str, count: int, spacing: float, distance: float) -> list[Vector2]:
    """La formación mirando hacia +x, con cada miembro a `distance` o más del origen y
    cada par de vecinos a `spacing`."""
    match kind:
        case "single":
            if count != 1:
                raise ValueError(f"single: es de a uno, no de a {count}")
            return [Vector2(distance, 0)]
        case "ring":
            # El arco de radio `distance` cuya cuerda mide `spacing`: 2·asin(s / 2d).
            step = 2 * math.asin(min(1.0, spacing / (2 * distance)))
            first = -step * (count - 1) / 2
            return [
                Vector2(distance, 0).rotate_rad(first + k * step) for k in range(count)
            ]
        case "line":
            first = -spacing * (count - 1) / 2
            return [Vector2(distance, first + k * spacing) for k in range(count)]
        case "cluster":
            # Un centro y sus vecinos en la red triangular, corridos hacia afuera para
            # que el más cercano al jugador quede a `distance`.
            around = lattice(Vector2(), count - 1, spacing)
            center = Vector2(distance + max((p.length() for p in around), default=0), 0)
            return [center] + [center + p for p in around]
    raise ValueError(f"formación desconocida: {kind}")


def _into_quadrant(shape: list[Vector2], q: int, rng: random.Random) -> list[Vector2]:
    """Gira la formación a un ángulo al azar dentro del cuadrante `q`, sin que ningún
    miembro se salga. Si es más ancha que el cuadrante, la centra."""
    half = max(abs(math.atan2(p.y, p.x)) for p in shape)
    low, high = q * QUARTER + half, (q + 1) * QUARTER - half
    angle = rng.uniform(low, high) if low < high else (low + high) / 2
    return [p.rotate_rad(angle) for p in shape]


def _crowded(
    points: list[Vector2],
    radius: float,
    occupied: Sequence[tuple[Vector2, float]],
    reach: float,
) -> bool:
    """Si algún miembro queda dentro del núcleo duro de alguno de `occupied`."""
    return any(
        p.distance_to(o) <= reach * (radius + r) for p in points for o, r in occupied
    )


def place_formation(
    kind: str,
    count: int,
    radius: float,
    occupied: Sequence[tuple[Vector2, float]],
    spec: SpawningSpec,
    reach: float,
    rng: random.Random,
) -> list[Vector2]:
    """Dónde nace una formación de `count` enemigos de `radius`, relativo al jugador.

    `occupied` son los enemigos vivos y los de la cola, como `(offset, radio)`. La
    formación cae en uno de sus cuadrantes más vacíos, y si empata, decide `rng`. Sus
    vecinos quedan a `reach · 2r + formation_gap`, fuera del núcleo duro. Si un miembro
    cae dentro del núcleo de otro enemigo, la formación entera se corre hacia afuera
    de a una separación, hasta quedar libre (decisión 27). Se corre en su propia
    dirección, así que no sale de su cuadrante ni se acerca al jugador.
    """
    spacing = reach * 2 * radius + spec.formation_gap
    shape = _shape(kind, count, spacing, spec.distance)
    q = rng.choice(emptiest_quadrants(o for o, _ in occupied))
    points = _into_quadrant(shape, q, rng)
    outward = sum(points, Vector2()).normalize()
    while _crowded(points, radius, occupied, reach):
        points = [p + outward * spacing for p in points]
    return points


class SpawnQueue:
    """Lo comprado que espera aparecer, en orden de compra, como `(tipo, offset)`."""

    def __init__(self) -> None:
        self._items: deque[tuple[str, Vector2]] = deque()

    def push(self, items: Iterable[tuple[str, Vector2]]) -> None:
        """Agrega al final, en orden."""
        self._items.extend(items)

    def pop(self, limit: int) -> list[tuple[str, Vector2]]:
        """Saca los primeros `limit`, o los que haya."""
        return [self._items.popleft() for _ in range(min(limit, len(self._items)))]

    def __iter__(self) -> Iterator[tuple[str, Vector2]]:
        """Los que esperan, sin sacarlos."""
        return iter(self._items)
