"""La masa crítica: cuando el enjambre se carga hacia un lado del jugador, aparece el
círculo que lo reparte (spec de la 0.2.0, decisiones 48 a 50).

Qué tan cargado está se mide con la longitud media resultante de la estadística
circular, `R̄ = |Σ ûᵢ| / N`, donde `ûᵢ` es el vector unitario del jugador al enemigo `i`.
Solo suma direcciones: un enemigo lejos pesa lo mismo que uno cerca. Si te rodean
parejo, los vectores se anulan y `R̄ = 0`; si están todos del mismo lado, `R̄ = 1`.
"""

from collections.abc import Sequence

from pygame.math import Vector2

from circlebh.balance import Balance, CriticalMassSpec
from circlebh.world.director import bar_at


def mean_resultant_length(offsets: Sequence[Vector2]) -> float:
    """`R̄ = |Σ ûᵢ| / N` de los `offsets`, relativos al jugador. Sin offsets da 0.

    Un offset nulo, encima del jugador, cuenta en `N` sin sumar dirección."""
    if not offsets:
        return 0.0
    total = sum(
        (offset.normalize() for offset in offsets if offset.length_squared() > 0),
        Vector2(),
    )
    return total.length() / len(offsets)


def heavy_direction(offsets: Sequence[Vector2]) -> Vector2 | None:
    """Hacia dónde está cargado el enjambre: `Σ ûᵢ` normalizado. Si te rodean tan
    parejo que la suma da 0, no hay dirección y da `None`. El círculo nace por ahí,
    detrás del grupo (decisión 56)."""
    total = sum(
        (offset.normalize() for offset in offsets if offset.length_squared() > 0),
        Vector2(),
    )
    if total.length_squared() == 0:
        return None
    return total.normalize()


def check_critical_mass(balance: Balance) -> None:
    """Rechaza al crear el mundo una masa crítica sin sentido, nombrando el campo."""
    spec = balance.critical_mass
    if spec.enemy not in balance.enemies:
        raise ValueError(f"critical_mass.enemy: no existe el enemigo {spec.enemy}")
    if spec.count < 1:
        raise ValueError(
            f"critical_mass.count: tiene que ser al menos 1, no {spec.count}"
        )
    if not 0 <= spec.imbalance <= 1:
        raise ValueError(
            f"critical_mass.imbalance: tiene que estar entre 0 y 1, no {spec.imbalance}"
        )
    if spec.cooldown_bars < 0:
        raise ValueError(
            "critical_mass.cooldown_bars: no puede ser negativo, no"
            f" {spec.cooldown_bars}"
        )


class CriticalMass:
    """Decide en qué paso hay que comprar el círculo. Tiene tres estados:

    - **listo:** puede aparecer apenas se junte la masa crítica;
    - **presente:** hay uno vivo o en la cola, y no aparece otro;
    - **esperando:** murió, y espera `cooldown_bars` compases antes de volver a listo.

    Cuenta los compases con el tempo del director, como la fusión (ADR 0025).
    """

    def __init__(self, spec: CriticalMassSpec, bpm: float) -> None:
        self.spec = spec
        self.bpm = bpm
        self._was_present = False
        self._ready_at = 0.0
        """El compás desde el que puede aparecer otro. Al empezar, no hay espera."""

    def update(self, steps: int, present: bool, offsets: Sequence[Vector2]) -> bool:
        """Si hay que comprar un círculo en este paso.

        `present` dice si hay uno vivo o en la cola, y `offsets` son los enemigos que
        cuentan, relativos al jugador. Cuando el círculo deja de estar presente, empieza
        la espera."""
        bar = bar_at(steps, self.bpm)
        if present:
            self._was_present = True
            return False
        if self._was_present:
            self._was_present = False
            self._ready_at = bar + self.spec.cooldown_bars
        if bar < self._ready_at:
            return False
        return (
            len(offsets) >= self.spec.count
            and mean_resultant_length(offsets) >= self.spec.imbalance
        )
