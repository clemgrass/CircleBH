"""Los patrones de movimiento: la conducta de cada tipo de enemigo (ADR 0021).

Cada patrón aporta una aceleración, y el enemigo suma las de todos sus patrones. Así, la
conducta de un tipo se declara en el balance como una lista de patrones, y cada uno se
lee como un término del potencial que el enemigo baja.

Cada enemigo tiene sus propias instancias: el balance da los números, y el estado que un
patrón necesite (por ejemplo, un timer) vive aquí.
"""

from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

from pygame.math import Vector2

from circlebh.balance import ChargesSpec, CoulombSpec, PatternSpec, SeekSpec
from circlebh.world.charges import pair_force, player_force

if TYPE_CHECKING:
    from circlebh.world.enemy import Enemy


@dataclass(frozen=True)
class Context:
    """Lo que un patrón puede mirar en este paso."""

    player_position: Vector2
    player_charge: float
    charges: ChargesSpec
    neighbors: Sequence[Enemy]
    """Los enemigos a menos de `charges.cutoff`. Puede incluir al propio enemigo."""


class Pattern(ABC):
    """La base de todo patrón de movimiento."""

    @abstractmethod
    def acceleration(self, enemy: Enemy, context: Context) -> Vector2:
        """La aceleración que este patrón le aporta a `enemy` en este paso."""


class Seek(Pattern):
    """Una aceleración de largo `strength` hacia el jugador, como una gravedad que apunta
    hacia él. Su potencial es un cono: `m · strength · |p − jugador|`."""

    def __init__(self, spec: SeekSpec) -> None:
        self.spec = spec

    def acceleration(self, enemy: Enemy, context: Context) -> Vector2:
        """Encima del jugador no hay dirección, y vale 0."""
        direction = context.player_position - enemy.position
        if direction.length_squared() == 0:
            return Vector2()
        return direction.normalize() * self.spec.strength


class Coulomb(Pattern):
    """El enemigo siente la ley de cargas: la de sus vecinos y la del jugador.

    `aᵢ = (Σⱼ F(pᵢ − pⱼ) + F_jugador(pᵢ − P)) / mᵢ`, con las fuerzas de `charges.py`.
    """

    def acceleration(self, enemy: Enemy, context: Context) -> Vector2:
        force = player_force(
            enemy.position - context.player_position,
            enemy.charge,
            context.player_charge,
            context.charges,
        )
        for other in context.neighbors:
            if other is enemy:
                continue
            force += pair_force(
                enemy.position - other.position,
                enemy.charge,
                other.charge,
                enemy.radius + other.radius,
                context.charges,
            )
        return force / enemy.mass


def make_pattern(spec: PatternSpec) -> Pattern:
    """La instancia del patrón que describe `spec`, nueva para cada enemigo."""
    match spec:
        case SeekSpec():
            return Seek(spec)
        case CoulombSpec():
            return Coulomb()
