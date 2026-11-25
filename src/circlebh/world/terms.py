"""Los términos de un arma: avance, armónicos y giro (ADR 0029).

La posición de lo que dispara un arma es una función pura de su `spec` y del tiempo `t`
desde el disparo, escrita como su fórmula. Va en el marco local del disparo, con
`û = (1, 0)`: quien la usa la lleva al plano. Así la usan igual el arma, los tests y,
más adelante, el dibujo de la tarjeta.
"""

import math

from pygame.math import Vector2

from circlebh.balance import WeaponSpec


def advance_at(spec: WeaponSpec, t: float) -> float:
    """El avance `a(t)`: `v·τ` con grado 0, `v·t` con grado 1 y `v·t²/(2τ)` con grado 2.

    Cada grado es la integral del anterior, dividida por `τ` para seguir siendo un
    largo: por eso `d/dt` y `∫dt` se deshacen uno al otro.
    """
    v, tau = spec.advance.coefficient, spec.tau
    match spec.advance.degree:
        case 0:
            return v * tau
        case 1:
            return v * t
        case 2:
            return v * t * t / (2 * tau)
        case degree:
            raise ValueError(f"advance.degree: tiene que ser 0, 1 o 2, llegó {degree}")


def harmonics_at(spec: WeaponSpec, t: float) -> float:
    """La suma de los armónicos, `Σ A·sin(k·t + φ)`. Sin armónicos, 0."""
    return sum(h.amplitude * math.sin(h.k * t + h.phase) for h in spec.harmonics)


def projectile_offset(spec: WeaponSpec, t: float) -> Vector2:
    """Dónde está el proyectil `t` segundos después del disparo, en el marco local.

    - Cartesiano: `(a(t), Σ A·sin(k·t + φ))`. Avanza por `û` y se desvía por la normal.
    - Polar: `(a(t) + Σ A·sin(k·t + φ))·(cos Ωt, sin Ωt)`. El radio gira con `Ω`.
    """
    along = advance_at(spec, t)
    wave = harmonics_at(spec, t)
    if spec.frame == "cartesian":
        return Vector2(along, wave)
    r = along + wave
    angle = spec.spin * t
    return Vector2(r * math.cos(angle), r * math.sin(angle))
