"""El barrido: cómo daña un trazo (ADR 0029 y 0032).

Cada paso, la curva se muestrea en puntos, y cada punto es una bala durante ese paso:
su tramo va de donde estaba ese mismo punto de la curva en el paso anterior a donde está
ahora, y se prueba con `Enemy.hit_by`, en el marco del enemigo. No hay una regla de daño
nueva: es la física de la bala.

Como la bala, el trazo se gasta donde pega (ADR 0032): quién lo usa saca de la curva el
arco que cubría al enemigo golpeado. Aquí solo se decide qué líneas se quitan.
"""

import math
from collections import defaultdict

from pygame.math import Vector2

from circlebh.world.enemy import Enemy
from circlebh.world.events import Hit
from circlebh.world.polygon import ENVELOPE_SLACK

CELL_SIZE = 32.0
"""El lado de las celdas en que se agrupan los puntos, en unidades del plano. Solo cambia
cuánto se demora el filtro, no lo que encuentra."""


class PointGrid:
    """Los puntos de un trazo agrupados en celdas de `CELL_SIZE`, para buscar los que
    quedan cerca de un enemigo sin recorrerlos todos (ADR 0020)."""

    def __init__(self, points: list[Vector2]) -> None:
        self.points = points
        self._cells: defaultdict[tuple[int, int], list[int]] = defaultdict(list)
        for i, p in enumerate(points):
            self._cells[_cell(p.x), _cell(p.y)].append(i)
        # La franja que ocupan los puntos alrededor de su centroide, `[dmin, dmax]`.
        # En un anillo es casi una circunferencia, así que descarta a casi todos.
        self._centroid = sum(points, Vector2()) / len(points) if points else Vector2()
        distances = [p.distance_to(self._centroid) for p in points]
        self._band = (min(distances, default=0.0), max(distances, default=0.0))

    def near(self, center: Vector2, radius: float) -> list[int]:
        """Los índices de los puntos a lo más `radius` de `center`, de menor a mayor.

        Primero descarta con la franja: un punto a lo más `radius` de `center` está a
        `d ± radius` del centroide, con `d` la distancia de `center` al centroide. Si
        ese intervalo no corta `[dmin, dmax]`, no hay ninguno. El margen de
        `ENVELOPE_SLACK`, en la franja y en las celdas, evita que el redondeo descarte un
        punto justo en el borde, o en la celda vecina por una diferencia diminuta."""
        d = center.distance_to(self._centroid)
        margin = radius + ENVELOPE_SLACK
        if d + margin < self._band[0] or d - margin > self._band[1]:
            return []
        found = []
        for cx in range(_cell(center.x - margin), _cell(center.x + margin) + 1):
            for cy in range(_cell(center.y - margin), _cell(center.y + margin) + 1):
                found += [
                    i
                    for i in self._cells.get((cx, cy), ())
                    if self.points[i].distance_squared_to(center) <= radius * radius
                ]
        return sorted(found)


def query_radius(enemy: Enemy, longest: float) -> float:
    """Hasta qué distancia de `enemy.position` puede estar un punto que golpea a `enemy`
    en este paso, si ningún punto avanzó más de `longest`.

    Un golpe pide que el tramo, en el marco del enemigo, pase a menos de `r` del centro,
    así que `d₁ ≤ r + L`, con `d₁` la distancia del punto al centro de ahora y `L` el
    largo de ese tramo. Mover el punto `P`, el enemigo `C` y girarlo `ω` lo acota:
    `L ≤ (1 + ω)(P + C) + ω·d₁`. Despejando, `d₁ ≤ (r + (1 + ω)(P + C)) / (1 − ω)`.
    Con `ω ≥ 1` (más de un radián por paso) no hay cota y el filtro no descarta nada.
    """
    r = enemy.radius + ENVELOPE_SLACK
    turn = abs(enemy.angle - enemy.previous_angle)
    if turn >= 1:
        return math.inf
    moved = enemy.position.distance_to(enemy.previous)
    return (r + (1 + turn) * (longest + moved)) / (1 - turn)


def strike(
    previous: list[Vector2],
    points: list[Vector2],
    enemies: list[Enemy],
    lines: int,
) -> list[Hit]:
    """Barre un paso: el punto `i` va de `previous[i]` a `points[i]`, como una bala.

    A cada enemigo le quita a lo más `lines` líneas, las primeras que la curva cruza en
    el paso, y devuelve un `Hit` por cada una. Varios puntos que cruzan al mismo enemigo
    en el mismo paso son un solo contacto.
    """
    grid = PointGrid(points)
    longest = max(
        (a.distance_to(b) for a, b in zip(previous, points, strict=True)),
        default=0.0,
    )
    hits: list[Hit] = []
    for enemy in enemies:
        near = grid.near(enemy.position, query_radius(enemy, longest))
        crossings = sorted(
            (crossing[0], i, crossing[1])
            for i in near
            if (crossing := enemy.hit_by(previous[i], points[i])) is not None
        )
        removed = 0
        for _, _, k in crossings:
            if removed >= lines:
                break
            # Varios puntos pueden cruzar la misma línea en el mismo paso.
            if k in enemy.edges:
                enemy.remove_edge(k)
                hits.append(Hit(enemy, k))
                removed += 1
    return hits


def _cell(coordinate: float) -> int:
    return math.floor(coordinate / CELL_SIZE)
