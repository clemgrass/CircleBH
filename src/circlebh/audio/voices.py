"""Las voces: cómo suena cada enemigo y cada arma (ADR 0022).

Un enemigo de n líneas es un loop E(n, 16) que suena mientras vive. Su ángulo alrededor
del jugador rota el loop, y el golpe i es la línea i: si la línea no está, ese golpe
calla. La nota del golpe i es la nota i del acorde que suena, así que nunca desafina.

Un arma es un loop E(k, 16) con k calculado desde su `spec` actual: una mejora se oye.
"""

import math
from collections.abc import Sequence
from dataclasses import dataclass

from pygame.math import Vector2

from circlebh.audio.rhythm import SIXTEENTHS, euclid
from circlebh.balance import Shape, WeaponSpec
from circlebh.world.enemy import Enemy

MAX_LOOPS = 3
"""Cuántos enemigos tienen loop: los más cercanos. Los demás solo suben la intensidad."""
LOOP_GAIN = 0.30
GAIN_DISTANCE = 450.0
"""El volumen de un loop es `LOOP_GAIN · e^(−d/GAIN_DISTANCE)`."""


@dataclass(frozen=True)
class EnemyView:
    """Lo que la música necesita de un enemigo, visto desde el jugador."""

    angle: float
    """De 0 a 2π, antihorario desde +x (ADR 0003)."""
    distance: float
    shape: Shape
    edges: tuple[int, ...]


@dataclass(frozen=True)
class Note:
    """Una nota de un loop de enemigo."""

    semitones: int
    """Desde La3, ya dentro del voicing del acorde (o una octava arriba)."""
    shape: Shape
    edges: tuple[int, ...]
    """La forma que le queda al enemigo: es el timbre de la nota."""
    gain: float


def nearest_views(
    enemies: Sequence[Enemy], player: Vector2, limit: int = MAX_LOOPS
) -> list[EnemyView]:
    """Los `limit` enemigos más cercanos al jugador, del más cercano al más lejano.

    Con el centro justo sobre el jugador no hay dirección: `atan2(0, 0)` da 0.
    """
    ordered = sorted(
        enemies, key=lambda enemy: enemy.position.distance_squared_to(player)
    )
    views = []
    for enemy in ordered[:limit]:
        offset = enemy.position - player
        angle = math.atan2(offset.y, offset.x) % math.tau
        views.append(
            EnemyView(angle, offset.length(), enemy.spec.shape, tuple(enemy.edges))
        )
    return views


def rotation(angle: float) -> int:
    """Cuántas semicorcheas se corre el loop: el ángulo llevado a 16 partes.

    El `% SIXTEENTHS` final hace que un ángulo de casi 2π redondee a 0 y no a 16.
    """
    return round(angle / math.tau * SIXTEENTHS) % SIXTEENTHS


def _loop_hit(view: EnemyView, s: int) -> int | None:
    """Qué golpe del loop cae en la semicorchea `s` del compás, o `None`.

    Con más líneas que semicorcheas, el loop es E(16, 16): un golpe en cada una.
    """
    pattern = euclid(min(view.shape.line_count, SIXTEENTHS), SIXTEENTHS)
    step = (s - rotation(view.angle)) % SIXTEENTHS
    if not pattern[step]:
        return None
    return sum(pattern[:step])


def _still_has(view: EnemyView, j: int) -> bool:
    """Si el golpe `j` todavía suena: su línea sigue ahí.

    Con más de 16 líneas, el golpe j es un grupo: suena mientras quede alguna línea
    con `k·16 // líneas == j`.
    """
    lines = view.shape.line_count
    if lines <= SIXTEENTHS:
        return j in view.edges
    return any(edge * SIXTEENTHS // lines == j for edge in view.edges)


def enemy_notes(
    views: Sequence[EnemyView], s: int, voicing: tuple[int, ...]
) -> list[Note]:
    """Las notas que tocan los loops de `views` en la semicorchea `s` del compás.

    `views` va del más cercano al más lejano. El más cercano suena una octava arriba.
    """
    notes = []
    for rank, view in enumerate(views):
        j = _loop_hit(view, s)
        if j is None or not _still_has(view, j):
            continue
        semitones = voicing[j % len(voicing)] + 12 * (rank == 0)
        gain = LOOP_GAIN * math.exp(-view.distance / GAIN_DISTANCE)
        notes.append(Note(semitones, view.shape, view.edges, gain))
    return notes


def weapon_note(s: int, voicing: tuple[int, ...]) -> int:
    """La nota de un golpe de arma: alterna la segunda y la cuarta nota del voicing, una
    octava arriba."""
    return voicing[1 if (s // 2) % 2 == 0 else 3] + 12


def weapon_pattern(spec: WeaponSpec, bar_seconds: float) -> list[bool]:
    """El loop de un arma en un compás de `bar_seconds`, desde su `spec` actual:
    E(k, 16), con k = los disparos que caben en un compás, entre 1 y 16.

    La voz sale del `spec` y no de la clase del arma, así que dos armas con el mismo
    `spec` suenan igual (ADR 0029).
    """
    k = round(bar_seconds / spec.cooldown)
    return euclid(max(1, min(SIXTEENTHS, k)), SIXTEENTHS)
