"""El cuerpo rígido: la pose de un enemigo que gira (ADR 0027).

La pose es la posición `c` y el ángulo `θ`. Un punto `q` del marco del enemigo está en
el plano en `c + R(θ)·q`, donde `R(θ)` gira en `θ` en sentido antihorario (ADR 0003).
"""

from collections.abc import Sequence

from pygame.math import Vector2


def to_local(point: Vector2, position: Vector2, angle: float) -> Vector2:
    """`point` visto desde el enemigo de pose `(position, angle)`: `R(−θ)·(p − c)`."""
    return (point - position).rotate_rad(-angle)


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
    return position + local.rotate_rad(angle)
