"""Parámetros de las entidades del juego, como dataclasses (ADR 0004).

Este archivo y `balance.json` deben calzar siempre; ninguno manda. Si difieren, el juego
no abre y `poe balance-chequear` nombra el campo. Para igualarlos:

- `poe balance-exportar` escribe `balance.json` desde este archivo.
- `poe balance-importar` reescribe el bloque de datos del final desde `balance.json`.
  Las clases, con sus tipos y docstrings, se escriben a mano y la importación no las toca.

Para agregar un campo, escríbelo en su clase y su valor en el bloque de datos, y después
exporta. Al revés no funciona: con un campo sin valor, este archivo no se puede importar.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class PlayerSpec:
    """El jugador."""

    speed: float
    """Velocidad máxima, en unidades del plano por segundo."""

    radius: float
    """Radio del círculo de choque, en unidades del plano."""


@dataclass(frozen=True)
class EnemySpec:
    """Un tipo de enemigo: un polígono regular que persigue al jugador."""

    sides: int
    """Lados al aparecer. Pierde uno por golpe y, sin lados, muere."""

    radius: float
    """Radio del círculo de choque con todos sus lados, en unidades del plano. Se achica
    en proporción a los lados que le quedan."""

    speed: float
    """Velocidad, en unidades del plano por segundo."""


@dataclass(frozen=True)
class SpawningSpec:
    """Cómo aparecen los enemigos."""

    distance: float
    """Distancia al jugador a la que aparecen, en unidades del plano. Tiene que quedar
    fuera de la vista: más que la esquina de la pantalla, más el radio del enemigo."""


@dataclass(frozen=True)
class CircleWeaponSpec:
    """El arma círculo: anillos que nacen en el jugador, crecen con `r(t) = growth_speed · t`
    y revientan al llegar a `max_radius`."""

    cooldown: float
    """Segundos entre un anillo y el siguiente."""

    growth_speed: float
    """Cuánto crece el radio, en unidades del plano por segundo."""

    max_radius: float
    """Radio al que el anillo revienta, en unidades del plano."""

    thickness: float
    """Grosor del trazo, en unidades del plano."""


@dataclass(frozen=True)
class Balance:
    """Todas las entidades del juego."""

    player: PlayerSpec
    """El jugador."""

    enemies: dict[str, EnemySpec]
    """Los tipos de enemigo, por nombre."""

    spawning: SpawningSpec
    """Cómo aparecen los enemigos."""

    circle_weapon: CircleWeaponSpec
    """El arma círculo."""


# >>> datos (lo genera poe balance-importar)
BALANCE = Balance(
    player=PlayerSpec(speed=240.0, radius=12.0),
    enemies={"hexagon": EnemySpec(sides=6, radius=24.0, speed=120.0)},
    spawning=SpawningSpec(distance=800.0),
    circle_weapon=CircleWeaponSpec(
        cooldown=1.5, growth_speed=300.0, max_radius=260.0, thickness=6.0
    ),
)
# <<< datos
