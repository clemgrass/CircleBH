"""Los enemigos: polígonos regulares hechos de líneas, que persiguen al jugador en línea
recta.

Cada línea es una parte del enemigo: la bala quita la que golpea, y sin líneas el enemigo
muere. Chocan por sus líneas, y el círculo envolvente es el primer descarte (ADR 0020).
"""

import math
import random

from pygame.math import Vector2

from circlebh.balance import EnemySpec
from circlebh.world.clock import STEP
from circlebh.world.collisions import segment_touches_circle
from circlebh.world.polygon import edge_sectors, first_hit, polygon_edge


class Enemy:
    """Un enemigo, en coordenadas del plano."""

    def __init__(self, spec: EnemySpec, position: Vector2) -> None:
        self.spec = spec
        self.position = Vector2(position)
        self.previous = Vector2(position)
        """Dónde estaba antes del último `step`. Lo usa el tramo relativo de `hit_by`."""
        self.edges = list(range(spec.sides))
        """Las aristas que le quedan, de menor a mayor (ver `polygon.py`)."""

    @property
    def radius(self) -> float:
        """Radio del círculo envolvente: el del polígono completo. No es un hitbox: las
        líneas que quedan no se mueven, así que no se achica."""
        return self.spec.radius

    @property
    def alive(self) -> bool:
        """Vive mientras le quede alguna línea."""
        return bool(self.edges)

    def remove_edge(self, k: int) -> None:
        """Quita la arista `k`: una bala la golpeó."""
        self.edges.remove(k)

    def lines(self) -> list[tuple[Vector2, Vector2]]:
        """Las líneas que le quedan, en coordenadas del plano."""
        return [
            (self.position + a, self.position + b)
            for a, b in (
                polygon_edge(self.spec.radius, self.spec.sides, k) for k in self.edges
            )
        ]

    def hit_by(self, start: Vector2, end: Vector2) -> tuple[float, int] | None:
        """La primera línea que cruza el tramo de una bala en el último paso, como `(t, k)`.

        `start` y `end` son dónde estaba la bala antes y después del paso. El tramo se
        mide desde el enemigo, que también se movió: de `start − previous` a
        `end − position`. Como el enemigo solo se traslada, ese tramo relativo es exacto, y
        un enemigo que avanza hacia la bala no la deja pasar entre dos pasos.
        """
        relative_start = start - self.previous
        relative_end = end - self.position
        if not segment_touches_circle(
            relative_start, relative_end, Vector2(), self.radius
        ):
            return None
        sides = self.spec.sides
        candidates = [
            k
            for k in edge_sectors(relative_start, relative_end, sides)
            if k in self.edges
        ]
        return first_hit(relative_start, relative_end, self.radius, sides, candidates)

    def step(self, target: Vector2) -> None:
        """Avanza un paso en línea recta hacia `target`, sin pasarse.

        `move_towards` no normaliza cuando ya está encima: no divide por cero y,
        si el objetivo queda a menos de un paso, llega justo y no oscila.
        """
        self.previous = Vector2(self.position)
        self.position = self.position.move_towards(target, self.spec.speed * STEP)


def spawn_position(center: Vector2, distance: float, rng: random.Random) -> Vector2:
    """Un punto a `distance` de `center`, en un ángulo al azar de la `rng` inyectada."""
    angle = rng.uniform(0, math.tau)
    return center + Vector2(math.cos(angle), math.sin(angle)) * distance
