"""El peligro del modo infinito: lo que compra el excedente sobre el tope de cuerpos.

Con el tope lleno, el presupuesto que no se puede gastar en cuerpos sube tres
multiplicadores, cada uno con su tope (decisiones 20 y 74 de la spec de la 0.2.0).
"""

import math
from dataclasses import dataclass

from circlebh.balance import EndlessSpec


@dataclass(frozen=True)
class Danger:
    """Multiplicadores que un enemigo recibe al nacer. `1` es como en el tema."""

    speed: float = 1.0
    """Multiplica la velocidad de los que persiguen: su tope y su empuje."""

    cadence: float = 1.0
    """Multiplica la cadencia de los ataques: sus `cooldown` duran `1/cadence`."""

    sides: float = 1.0
    """Carga el mazo hacia los de más lados: cada peso por `(n/3)^(sides − 1)`."""


NEUTRAL = Danger()
"""El peligro de todo enemigo fuera del infinito."""


def danger_at(excess: float, base: float, spec: EndlessSpec) -> Danger:
    """El peligro con un excedente `excess`, en un infinito que parte con `base`.

    El nivel es `ℓ = log₂(1 + E/B₀)`: cuántas veces se duplicó el excedente, medido en
    lo que gana el primer compás. Como `E` crece de forma exponencial, `ℓ` crece parejo
    en el tiempo, y cada multiplicador, `1 + step·ℓ`, también, hasta su tope.
    """
    level = math.log2(1 + excess / base)

    def capped(cap: float) -> float:
        return min(cap, 1 + spec.step * level)

    return Danger(
        capped(spec.speed_cap), capped(spec.cadence_cap), capped(spec.sides_cap)
    )
