"""La ley de cargas: las fuerzas entre enemigos y la atracción del jugador (ADR 0021).

Todas son fuerzas, no aceleraciones: quien las usa divide por la masa. Entre dos
enemigos, la fuerza es simétrica (tercera ley de Newton): la de `j` sobre `i` es la
contraria de la de `i` sobre `j`, así que la cantidad de movimiento se conserva.
"""

import math

from pygame.math import Vector2

from circlebh.balance import ChargesSpec

# `math.pow` y no `**`: con exponente real, `**` puede dar un complejo y mypy lo tipa
# como `Any`. `math.pow` siempre da un `float`.


def pair_force(
    offset: Vector2, qi: float, qj: float, contact: float, spec: ChargesSpec
) -> Vector2:
    """La fuerza sobre `i` desde `j`, con `offset = pᵢ − pⱼ` y `contact = rᵢ + rⱼ`.

    Con `r = |offset|`, es `(f(r) + g(r)) · offset / r`, positiva cuando repele:

    - Coulomb, `f(r) = k·qᵢ·qⱼ·[r / (r² + ε²)^{3/2} − rc / (rc² + ε²)^{3/2}]` si
      `r < rc`. `ε` la deja finita cerca de 0, y restar su valor en `rc` hace que llegue
      a 0 justo en el corte, sin saltar.
    - El núcleo duro, `g(r) = K·((d₀ / r)ⁿ − 1)` si `r < d₀ = core_reach · contact`. No
      depende de las cargas: siempre repele, aunque los polos se atraigan.

    En el mismo punto no hay dirección: da `Vector2()`, y los separa la red de seguridad.
    """
    r = offset.length()
    if r == 0:
        return Vector2()
    magnitude = 0.0
    if r < spec.cutoff:
        magnitude += (
            spec.k
            * qi
            * qj
            * (_softened(r, spec.softening) - _softened(spec.cutoff, spec.softening))
        )
    reach = spec.core_reach * contact
    if r < reach:
        magnitude += spec.core_strength * (math.pow(reach / r, spec.core_exponent) - 1)
    return offset * (magnitude / r)


def player_force(
    offset: Vector2, q: float, player_charge: float, spec: ChargesSpec
) -> Vector2:
    """La fuerza sobre un enemigo de carga `q` desde el jugador, con `offset = p − jugador`.

    Es Coulomb, `k·q·q_p·offset / (r² + ε_p²)^{3/2}`, sin corte y sin núcleo: un solo
    cuerpo cuesta poco, y sin núcleo un enemigo abierto puede quedar alrededor del
    jugador. Con `ε_p` del orden del radio del enemigo, cerca del centro actúa como un
    resorte, `≈ k·q·q_p·offset / ε_p³`, y en el mismo punto vale 0.
    """
    r_squared = offset.length_squared()
    softened = math.pow(r_squared + spec.player_softening**2, 1.5)
    return offset * (spec.k * q * player_charge / softened)


def _softened(r: float, epsilon: float) -> float:
    """`r / (r² + ε²)^{3/2}`: el `1/r²` de Coulomb, suavizado cerca de 0."""
    return r / math.pow(r * r + epsilon * epsilon, 1.5)
