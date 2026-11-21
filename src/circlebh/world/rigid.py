"""El cuerpo rígido: la pose de un enemigo que gira (ADR 0027).

La pose es la posición `c` y el ángulo `θ`. Un punto `q` del marco del enemigo está en
el plano en `c + R(θ)·q`, donde `R(θ)` gira en `θ` en sentido antihorario (ADR 0003).
"""

import math
from collections.abc import Sequence

from pygame.math import Vector2


def rotate(vector: Vector2, angle: float) -> Vector2:
    """`R(θ)·v = (x·cos θ − y·sen θ, x·sen θ + y·cos θ)`: gira `v` en `θ`, antihorario.

    No usa `Vector2.rotate_rad`: en pygame-ce 2.5.8, ese método redondea a exacto los
    ángulos muy cerca de un múltiplo de 90°, y no igual hacia los dos lados. Por eso
    `rotate_rad(θ)` y `rotate_rad(−θ)` dejaban de ser inversas (2026-11-21, observado
    con `θ = 1e-6`)."""
    cos, sin = math.cos(angle), math.sin(angle)
    return Vector2(vector.x * cos - vector.y * sin, vector.x * sin + vector.y * cos)


def to_local(point: Vector2, position: Vector2, angle: float) -> Vector2:
    """`point` visto desde el enemigo de pose `(position, angle)`: `R(−θ)·(p − c)`."""
    return rotate(point - position, -angle)


def center_of_mass(lines: Sequence[tuple[Vector2, Vector2]]) -> Vector2:
    """El centro de masa de `lines`: `Σ mᵢ·pᵢ / Σ mᵢ`, con la masa de cada línea en su
    punto medio `pᵢ` y proporcional a su largo `mᵢ`."""
    if not lines:
        raise ValueError("center_of_mass: sin líneas no hay centro de masa")
    total = sum(((a - b).length() for a, b in lines), 0.0)
    weighted = sum(((a + b) / 2 * (a - b).length() for a, b in lines), Vector2())
    return weighted / total


def to_world(local: Vector2, position: Vector2, angle: float) -> Vector2:
    """El punto `local` del enemigo, en el plano: `c + R(θ)·q`."""
    return position + rotate(local, angle)
