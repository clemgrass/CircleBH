"""Las voces: cómo suena cada enemigo y cada arma (ADR 0022).

Un enemigo de n lados es un loop E(n, 16) que suena mientras vive. Su ángulo alrededor
del jugador rota el loop, y el golpe i es la arista i: si la arista no está, ese golpe
calla. La nota del golpe i es la nota i del acorde que suena, así que nunca desafina.

Un arma es un loop E(k, 16) con k calculado desde su `spec` actual: una mejora se oye.
Cada clase de arma declara su voz en `VOICES`.
"""

import math
from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass

from pygame.math import Vector2

from circlebh.audio.rhythm import SIXTEENTHS, euclid
from circlebh.world.enemy import Enemy
from circlebh.world.weapons import PointWeapon, Weapon

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
    sides: int
    edges: tuple[int, ...]


@dataclass(frozen=True)
class Note:
    """Una nota de un loop de enemigo."""

    semitones: int
    """Desde La3, ya dentro del voicing del acorde (o una octava arriba)."""
    sides: int
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
            EnemyView(angle, offset.length(), enemy.spec.sides, tuple(enemy.edges))
        )
    return views


def rotation(angle: float) -> int:
    """Cuántas semicorcheas se corre el loop: el ángulo llevado a 16 partes.

    El `% SIXTEENTHS` final hace que un ángulo de casi 2π redondee a 0 y no a 16.
    """
    return round(angle / math.tau * SIXTEENTHS) % SIXTEENTHS


def _loop_hit(view: EnemyView, s: int) -> int | None:
    """Qué golpe del loop cae en la semicorchea `s` del compás, o `None`.

    Con más lados que semicorcheas, el loop es E(16, 16): un golpe en cada una.
    """
    pattern = euclid(min(view.sides, SIXTEENTHS), SIXTEENTHS)
    step = (s - rotation(view.angle)) % SIXTEENTHS
    if not pattern[step]:
        return None
    return sum(pattern[:step])


def _still_has(view: EnemyView, j: int) -> bool:
    """Si el golpe `j` todavía suena: su arista sigue ahí.

    Con más de 16 lados, el golpe j es un sector: suena mientras quede alguna arista
    con `k·16 // lados == j`.
    """
    if view.sides <= SIXTEENTHS:
        return j in view.edges
    return any(edge * SIXTEENTHS // view.sides == j for edge in view.edges)


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
        notes.append(Note(semitones, view.sides, view.edges, gain))
    return notes


def weapon_note(s: int, voicing: tuple[int, ...]) -> int:
    """La nota de un golpe de arma: alterna la segunda y la cuarta nota del voicing, una
    octava arriba."""
    return voicing[1 if (s // 2) % 2 == 0 else 3] + 12


class WeaponVoice(ABC):
    """El ritmo de una clase de arma."""

    @abstractmethod
    def pattern(self, weapon: Weapon, bar_seconds: float) -> list[bool]:
        """El loop del arma en un compás de `bar_seconds`, desde su `spec` actual."""


class PointVoice(WeaponVoice):
    """El arma punto: E(k, 16), con k = los disparos que caben en un compás."""

    def pattern(self, weapon: Weapon, bar_seconds: float) -> list[bool]:
        if not isinstance(weapon, PointWeapon):
            raise TypeError(
                f"PointVoice espera un PointWeapon, llegó {type(weapon).__name__}"
            )
        k = round(bar_seconds / weapon.spec.cooldown)
        return euclid(max(1, min(SIXTEENTHS, k)), SIXTEENTHS)


VOICES: dict[type[Weapon], WeaponVoice] = {PointWeapon: PointVoice()}
"""La voz de cada clase de arma. Un arma nueva suma aquí su voz."""


def _voice_of_type(cls: type) -> WeaponVoice | None:
    """La voz de la clase o, si no tiene, la de la clase más cercana de la que hereda:
    una subclase de un arma suena como su arma."""
    for base in cls.__mro__:
        if base in VOICES:
            return VOICES[base]
    return None


def has_voice(cls: type) -> bool:
    return _voice_of_type(cls) is not None


def voice_for(weapon: Weapon) -> WeaponVoice:
    voice = _voice_of_type(type(weapon))
    if voice is None:
        raise KeyError(f"{type(weapon).__name__} no tiene voz en audio/voices.py")
    return voice
