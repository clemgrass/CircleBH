"""El enjambre: el paso simultáneo de todos los enemigos y la red de seguridad (ADR 0021).

Primero se calculan todas las aceleraciones con las posiciones del inicio del paso, y
recién después se mueven todos. Así, el orden de la lista no cambia el resultado. Los
vecinos los encuentra la grilla espacial (ADR 0006).
"""

import math
from collections.abc import Sequence

from pygame.math import Vector2

from circlebh.balance import ChargesSpec
from circlebh.world.collisions import circles_touch
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

    Los fantasmas no entran: los demás los atraviesan, sin fuerzas ni red de seguridad.
    """
    alive = [enemy for enemy in enemies if enemy.alive and not enemy.spec.phantom]
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
    return separate(alive, charges.cutoff)


def separate(enemies: Sequence[Enemy], cell_size: float) -> int:
    """La red de seguridad: aparta a los pares cuyos círculos envolventes se superponen,
    y devuelve cuántos pares corrigió.

    Cada uno se lleva su parte `wᵢ / (wᵢ + wⱼ)` de la superposición, en la dirección
    que los une, y de la velocidad con que se acercan: el choque no rebota. El peso `w`
    es 1, o 0 si está anclado. Entre dos libres, cada uno se lleva la mitad; contra un
    anclado, el otro se lleva todo; y dos anclados no se corrigen. Las correcciones de
    todos los pares se suman y se aplican juntas (Jacobi), para que no dependan del
    orden de la lista. Un par aislado queda tangente; en un grupo puede quedar un
    resto, que se corrige en el paso siguiente.
    """
    shifts = [Vector2() for _ in enemies]
    pushes = [Vector2() for _ in enemies]
    corrected = 0
    for i, j in sorted(_close_pairs(enemies, cell_size)):
        a, b = enemies[i], enemies[j]
        wa, wb = _weight(a), _weight(b)
        offset = b.position - a.position
        overlap = a.radius + b.radius - offset.length()
        if overlap <= 0 or wa + wb == 0:
            continue
        corrected += 1
        share_a, share_b = wa / (wa + wb), wb / (wa + wb)
        normal = offset.normalize() if offset.length_squared() > 0 else FIXED_DIRECTION
        shifts[i] -= normal * (overlap * share_a)
        shifts[j] += normal * (overlap * share_b)
        approaching = (b.velocity - a.velocity).dot(normal)
        if approaching < 0:
            pushes[i] += normal * (approaching * share_a)
            pushes[j] -= normal * (approaching * share_b)
    for enemy, shift, push in zip(enemies, shifts, pushes, strict=True):
        enemy.position = enemy.position + shift
        enemy.velocity = enemy.velocity + push
    return corrected


def _weight(enemy: Enemy) -> float:
    """Cuánto le toca de cada corrección: 0 si está anclado, como de masa infinita."""
    return 0.0 if enemy.spec.anchored else 1.0


def _close_pairs(enemies: Sequence[Enemy], cell_size: float) -> set[tuple[int, int]]:
    """Los pares cuyos círculos envolventes se tocan, con `i < j`.

    Los cuerpos cuyo diámetro cabe en `cell_size` van a la grilla. Los pocos más grandes,
    como un jefe, se revisan contra todos: si la grilla usara celdas de su tamaño, cada
    celda juntaría a decenas de hexágonos y la búsqueda se volvería casi todos contra
    todos.
    """
    small = [i for i, enemy in enumerate(enemies) if 2 * enemy.radius <= cell_size]
    big = [i for i, enemy in enumerate(enemies) if 2 * enemy.radius > cell_size]
    found = {
        (small[a], small[b])
        for a, b in SpatialGrid(cell_size).pairs(
            [enemies[i].position for i in small], [enemies[i].radius for i in small]
        )
    }
    for i in big:
        for j in range(len(enemies)):
            if j != i and circles_touch(
                enemies[i].position,
                enemies[i].radius,
                enemies[j].position,
                enemies[j].radius,
            ):
                found.add((min(i, j), max(i, j)))
    return found


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
