"""El enjambre: el paso simultáneo de todos los enemigos y la red de seguridad (ADR 0021).

Primero se calculan todas las aceleraciones con las posiciones del inicio del paso, y
recién después se mueven todos. Así, el orden de la lista no cambia el resultado. Los
vecinos los encuentra la grilla espacial (ADR 0006).
"""

import math
from collections.abc import Sequence

from pygame.math import Vector2

from circlebh.balance import ChargesSpec
from circlebh.world.enemy import Enemy
from circlebh.world.grid import SpatialGrid
from circlebh.world.patterns import Context

FIXED_DIRECTION = Vector2(1, 0)
"""Hacia dónde se separan dos enemigos en el mismo punto exacto: ahí no hay dirección."""


def step_swarm(
    enemies: Sequence[Enemy],
    player_position: Vector2,
    player_charge: float,
    charges: ChargesSpec,
) -> int:
    """Avanza un paso a los enemigos vivos, y devuelve cuántos pares corrigió la red de
    seguridad.

    Los vecinos de cada uno son los que están a menos de `charges.cutoff`: con radio
    `cutoff / 2` para todos, "se tocan" en la grilla justo a esa distancia.
    """
    alive = [enemy for enemy in enemies if enemy.alive]
    half = charges.cutoff / 2
    pairs = SpatialGrid(charges.cutoff).pairs(
        [enemy.position for enemy in alive], [half] * len(alive)
    )
    neighbors: list[list[Enemy]] = [[] for _ in alive]
    # Ordenados, para que las sumas de cada uno vayan siempre en el mismo orden.
    for i, j in sorted(pairs):
        neighbors[i].append(alive[j])
        neighbors[j].append(alive[i])
    accelerations = [
        enemy.acceleration(
            Context(player_position, player_charge, charges, neighbors[k])
        )
        for k, enemy in enumerate(alive)
    ]
    for enemy, acceleration in zip(alive, accelerations, strict=True):
        enemy.step(acceleration)
    return separate(alive)


def separate(enemies: Sequence[Enemy]) -> int:
    """La red de seguridad: aparta a los pares cuyos círculos envolventes se superponen,
    y devuelve cuántos pares corrigió.

    A cada uno le toca la mitad de la superposición, en la dirección que los une, y se
    le quita la mitad de la velocidad con que se acercan: el choque no rebota. Las
    correcciones de todos los pares se suman y se aplican juntas (Jacobi), para que no
    dependan del orden de la lista. Un par aislado queda tangente; en un grupo puede
    quedar un resto, que se corrige en el paso siguiente.
    """
    if not enemies:
        return 0
    positions = [enemy.position for enemy in enemies]
    radii = [enemy.radius for enemy in enemies]
    pairs = SpatialGrid(2 * max(radii)).pairs(positions, radii)
    shifts = [Vector2() for _ in enemies]
    pushes = [Vector2() for _ in enemies]
    corrected = 0
    for i, j in sorted(pairs):
        a, b = enemies[i], enemies[j]
        offset = b.position - a.position
        overlap = a.radius + b.radius - offset.length()
        if overlap <= 0:
            continue
        corrected += 1
        normal = offset.normalize() if offset.length_squared() > 0 else FIXED_DIRECTION
        shifts[i] -= normal * (overlap / 2)
        shifts[j] += normal * (overlap / 2)
        approaching = (b.velocity - a.velocity).dot(normal)
        if approaching < 0:
            pushes[i] += normal * (approaching / 2)
            pushes[j] -= normal * (approaching / 2)
    for enemy, shift, push in zip(enemies, shifts, pushes, strict=True):
        enemy.position = enemy.position + shift
        enemy.velocity = enemy.velocity + push
    return corrected


def lattice(center: Vector2, count: int, spacing: float) -> list[Vector2]:
    """Los `count` puntos más cercanos a `center` de una red triangular de lado
    `spacing`, sin el centro, ordenados por distancia y después por ángulo.

    La red es `center + i·(1, 0)·spacing + j·(½, √3/2)·spacing`. Es el orden en que se
    acomodan las cargas que se repelen: cada punto tiene seis vecinos a `spacing`.
    """
    u = Vector2(spacing, 0)
    v = Vector2(spacing / 2, spacing * math.sqrt(3) / 2)
    n = math.isqrt(count) + 2
    while True:
        # El rombo de ±n pasos contiene entero el disco de radio n·spacing·√3/2.
        reach = n * spacing * math.sqrt(3) / 2
        offsets = [
            i * u + j * v
            for i in range(-n, n + 1)
            for j in range(-n, n + 1)
            if (i, j) != (0, 0) and (i * u + j * v).length() <= reach
        ]
        if len(offsets) >= count:
            break
        n += 1
    offsets.sort(key=lambda p: (round(p.length(), 9), math.atan2(p.y, p.x)))
    return [center + p for p in offsets[:count]]
