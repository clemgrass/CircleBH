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


def samples_for(spec: WeaponSpec, t: float, spacing: float) -> int:
    """Cuántos puntos tomar de un trazo polar en `t` para que dos seguidos queden a lo
    más `spacing`.

    La rapidez con que el punto recorre la curva al girar θ cumple
    `|dp/dθ| = √(ρ² + ρ'²) ≤ |ρ| + |ρ'|`, y cada armónico aporta a lo más `|A|` a `ρ`
    y `|A·k|` a `ρ'`. Con esa cota `B`, la vuelta mide a lo más `2π·B`, y `⌈2π·B /
    spacing⌉` puntos parejos en θ quedan a lo más `spacing`. Sin tope: la cantidad sale
    del largo de la curva (ADR 0029). Al menos uno, aunque el radio sea 0.
    """
    if spacing <= 0:
        raise ValueError(f"spacing: tiene que ser positivo, llegó {spacing}")
    bound = abs(_polar_base(spec, t)) + sum(
        abs(h.amplitude) * (1 + abs(h.k)) for h in spec.harmonics
    )
    return max(1, math.ceil(math.tau * bound / spacing))


def trace_points(spec: WeaponSpec, t: float, samples: int) -> list[Vector2]:
    """`samples` puntos del trazo polar `t` segundos después de lanzarlo, en el marco
    local centrado en el jugador, con θ parejo desde `û = (1, 0)`.

    `ρ(θ, t) = min(a(t), R) + Σ A·sin(k(θ − Ωt) + φ)`: el avance crece hasta `R`, y
    los armónicos ondulan la curva y giran con `Ω`. El punto `i` va en
    `θᵢ = 2π·i / samples`, así que el mismo `i` es el mismo punto de la curva en otro
    `t`: así se arma el tramo del barrido.
    """
    base = _polar_base(spec, t)
    points = []
    for i in range(samples):
        theta = math.tau * i / samples
        rho = base + sum(
            h.amplitude * math.sin(h.k * (theta - spec.spin * t) + h.phase)
            for h in spec.harmonics
        )
        points.append(Vector2(rho * math.cos(theta), rho * math.sin(theta)))
    return points


def _polar_base(spec: WeaponSpec, t: float) -> float:
    """El radio sin armónicos de un trazo polar: `min(a(t), R)`."""
    return min(advance_at(spec, t), spec.reach)
