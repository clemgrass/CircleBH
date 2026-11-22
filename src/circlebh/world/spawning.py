"""La aparición: dónde nace lo que compra el director, y cuántos por paso (ADR 0025).

Todo se mide relativo al jugador. Una compra nace en el cuadrante con menos enemigos,
contando los vivos y los que esperan en la cola, y a `spawning.distance` o más, fuera
de la vista. Lo comprado entra a una cola, y sale de a `max_per_step` por paso.
"""

import itertools
import math
import random
from collections import deque
from collections.abc import Iterable, Iterator, Sequence

from pygame.math import Vector2

from circlebh.balance import Balance, SpawningSpec
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
    if spec.formation_gap <= 0:
        # Con 0, los vecinos nacen justo en el borde del núcleo duro, no fuera de él.
        raise ValueError("spawning.formation_gap: tiene que ser mayor que 0")
    if spec.distance <= 0:
        raise ValueError("spawning.distance: tiene que ser mayor que 0")


def check_formations(balance: Balance) -> None:
    """Rechaza al empezar una formación del tema que no cabe en un cuadrante.

    Prueba cada tipo del mazo de cada sección con cada formación de la sección, en su
    tamaño mayor, que es el más ancho. Así falla al crear el mundo, nombrando el
    tamaño, y no a mitad de la partida.
    """
    spec = balance.spawning
    reach = balance.charges.core_reach
    for section in balance.director.sections:
        for entry, kind in itertools.product(section.deck, section.formations):
            count = 1 if kind == "single" else spec.formation_size[1]
            radius = balance.enemies[entry.enemy].radius
            _half_width(
                _shape(kind, count, _spacing(radius, spec, reach), spec.distance)
            )


def _spacing(radius: float, spec: SpawningSpec, reach: float) -> float:
    """La separación entre vecinos de una formación: fuera del núcleo duro, más el
    espacio libre `formation_gap`."""
    return reach * 2 * radius + spec.formation_gap


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
            if spacing >= 2 * distance:
                raise ValueError(
                    f"ring: una separación de {spacing:.0f} no cabe en un cuadrante"
                    f" a {distance:.0f} del jugador"
                )
            step = 2 * math.asin(spacing / (2 * distance))
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


def _half_width(shape: list[Vector2]) -> float:
    """El mayor ángulo de un miembro respecto de +x. Si pasa de 45°, la formación no
    cabe en un cuadrante y se rechaza."""
    half = max(abs(math.atan2(p.y, p.x)) for p in shape)
    if half > QUARTER / 2:
        raise ValueError(
            f"una formación de {len(shape)} mide {math.degrees(2 * half):.0f}°:"
            " no cabe en un cuadrante; baja spawning.formation_size"
        )
    return half


def _into_quadrant(shape: list[Vector2], q: int, rng: random.Random) -> list[Vector2]:
    """Gira la formación a un ángulo al azar dentro del cuadrante `q`, sin que ningún
    miembro se salga."""
    half = _half_width(shape)
    angle = rng.uniform(q * QUARTER + half, (q + 1) * QUARTER - half)
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
    angle: float | None = None,
) -> list[Vector2]:
    """Dónde nace una formación de `count` enemigos de `radius`, relativo al jugador.

    `occupied` son los enemigos vivos y los de la cola, como `(offset, radio)`. La
    formación cae en uno de sus cuadrantes más vacíos, y si empata, decide `rng`. Sus
    vecinos quedan a `reach · 2r + formation_gap`, fuera del núcleo duro. Si un miembro
    cae dentro del núcleo de otro enemigo, la formación entera se corre hacia afuera
    de a una separación, hasta quedar libre (decisión 27). Se corre en su propia
    dirección, así que no sale de su cuadrante ni se acerca al jugador.

    Con `angle`, la formación mira hacia ese ángulo, en radianes, en vez de sortear un
    cuadrante, y no saca números de `rng`. Así nace el círculo, detrás del grupo que lo
    trajo (decisión 56).
    """
    spacing = _spacing(radius, spec, reach)
    shape = _shape(kind, count, spacing, spec.distance)
    if angle is None:
        q = rng.choice(emptiest_quadrants(o for o, _ in occupied))
        points = _into_quadrant(shape, q, rng)
    else:
        points = [p.rotate_rad(angle) for p in shape]
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
