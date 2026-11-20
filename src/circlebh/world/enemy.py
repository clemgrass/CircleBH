"""Los enemigos: polígonos regulares que persiguen al jugador en línea recta.

Se dibujan como polígonos, pero chocan como círculos (ADR 0006).
"""

import math
import random

from pygame.math import Vector2

from circlebh.balance import EnemySpec
from circlebh.world.clock import STEP


class Enemy:
    """Un enemigo, en coordenadas del plano."""

    def __init__(self, spec: EnemySpec, position: Vector2) -> None:
        self.spec = spec
        self.position = Vector2(position)
        self.sides = spec.sides
        """Lados que le quedan. Por ahora no cambia; el daño llega con las balas."""

    @property
    def radius(self) -> float:
        """Radio del círculo de choque: se achica en proporción a los lados que le quedan."""
        return self.spec.radius * self.sides / self.spec.sides

    def step(self, target: Vector2) -> None:
        """Avanza un paso en línea recta hacia `target`, sin pasarse.

        `move_towards` no normaliza cuando ya está encima: no divide por cero y,
        si el objetivo queda a menos de un paso, llega justo y no oscila.
        """
        self.position = self.position.move_towards(target, self.spec.speed * STEP)


def spawn_position(center: Vector2, distance: float, rng: random.Random) -> Vector2:
    """Un punto a `distance` de `center`, en un ángulo al azar de la `rng` inyectada."""
    angle = rng.uniform(0, math.tau)
    return center + Vector2(math.cos(angle), math.sin(angle)) * distance
