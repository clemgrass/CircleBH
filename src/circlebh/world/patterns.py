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

from circlebh.balance import (
    ChargesSpec,
    CoulombSpec,
    OrbitSpec,
    PatternSpec,
    SeekSpec,
)
from circlebh.world.charges import pair_force, player_force

if TYPE_CHECKING:
    from circlebh.world.enemy import Enemy


@dataclass(frozen=True)
class Context:
    """Lo que un patrón puede mirar en este paso."""

    player_position: Vector2
    player_velocity: Vector2
    """En unidades / s, medida en el último paso del jugador."""
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
        """Encima del jugador no hay dirección, y vale 0. En el infinito, el peligro la
        multiplica: con el roce igual, la velocidad final `strength/γ` sube lo mismo."""
        direction = context.player_position - enemy.position
        if direction.length_squared() == 0:
            return Vector2()
        return direction.normalize() * self.spec.strength * enemy.danger.speed


class Coulomb(Pattern):
    """El enemigo siente la ley de cargas: la de sus vecinos y la del jugador.

    `aᵢ = (Σⱼ F(pᵢ − pⱼ) + F_jugador(pᵢ − P)) / mᵢ`, con las fuerzas de `charges.py`.
    """

    def acceleration(self, enemy: Enemy, context: Context) -> Vector2:
        # La carga propia se lee una vez: puede depender de sus acciones (decisión 57).
        charge = enemy.charge
        force = player_force(
            enemy.position - context.player_position,
            charge,
            context.player_charge,
            context.charges,
        )
        for other in context.neighbors:
            if other is enemy:
                continue
            force += pair_force(
                enemy.position - other.position,
                charge,
                other.charge,
                enemy.radius + other.radius,
                context.charges,
            )
        return force / enemy.mass


class Orbit(Pattern):
    """Un resorte radial hacia `r = R` y un empuje tangencial, en polares desde el
    jugador: `a = −stiffness·(r − R)·r̂ + tangential·θ̂`.

    `r̂` apunta del jugador al enemigo, y `θ̂ = (−r̂y, r̂x)` es `r̂` girado 90°
    antihorario. Sin tangencial, el enemigo se queda a distancia `R`, mirando.

    Con `follow`, suma `friction·u`, con `u` la velocidad del jugador: el roce se mide
    desde él, y el anillo viaja con quien corre.
    """

    def __init__(self, spec: OrbitSpec) -> None:
        self.spec = spec

    def acceleration(self, enemy: Enemy, context: Context) -> Vector2:
        """Encima del jugador no hay dirección radial, y el resorte y el empuje valen 0,
        como en `Seek`. El roce desde el jugador no la necesita, y sigue.

        En el infinito, el peligro multiplica el resorte y el empuje, pero no el roce
        desde el jugador: ese hace que el anillo viaje con él, y escalado lo dejaría
        atrás o lo haría correr más que él."""
        spec = self.spec
        carry = (
            context.player_velocity * enemy.spec.friction if spec.follow else Vector2()
        )
        offset = enemy.position - context.player_position
        r = offset.length()
        if r == 0:
            return carry
        radial = offset / r
        tangent = Vector2(-radial.y, radial.x)
        pull = (
            radial * (-spec.stiffness * (r - spec.radius)) + tangent * spec.tangential
        )
        return pull * enemy.danger.speed + carry


def make_pattern(spec: PatternSpec) -> Pattern:
    """La instancia del patrón que describe `spec`, nueva para cada enemigo."""
    match spec:
        case SeekSpec():
            return Seek(spec)
        case CoulombSpec():
            return Coulomb()
        case OrbitSpec():
            return Orbit(spec)
