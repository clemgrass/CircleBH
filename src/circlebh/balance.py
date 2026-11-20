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
from typing import Literal


@dataclass(frozen=True)
class PlayerSpec:
    """El jugador."""

    speed: float
    """Velocidad máxima, en unidades del plano por segundo."""

    radius: float
    """Radio del círculo de choque, en unidades del plano."""

    charge: float
    """Su carga eléctrica, de signo contrario a la de los enemigos: los atrae. Es una
    carga fija, como de masa infinita: ninguna fuerza lo mueve (ADR 0021)."""


@dataclass(frozen=True)
class ChargesSpec:
    """La ley de cargas entre cuerpos, una sola para todos (ADR 0021).

    Entre dos enemigos, a distancia `r`, la fuerza sobre cada uno es Coulomb más un
    núcleo duro, en la dirección que los une:

    - Coulomb: `k·qᵢ·qⱼ·[r / (r² + ε²)^{3/2} − rc / (rc² + ε²)^{3/2}]` si `r < rc`.
    - Núcleo: `K·((d₀ / r)ⁿ − 1)` si `r < d₀`, con `d₀ = core_reach · (rᵢ + rⱼ)`.

    Entre el jugador y un enemigo, solo Coulomb, sin corte y con su propio suavizado.
    """

    k: float
    """La constante de Coulomb, en unidades³ / s² por carga²."""

    cutoff: float
    """Distancia entre centros desde la que Coulomb entre enemigos vale 0. Es también el
    tamaño de celda de la grilla que busca vecinos."""

    softening: float
    """`ε`: suaviza Coulomb entre enemigos cerca de `r = 0`, en unidades del plano."""

    player_softening: float
    """`ε` de la atracción del jugador: cerca del centro actúa como un resorte."""

    core_strength: float
    """`K`: la fuerza del núcleo duro."""

    core_reach: float
    """Dónde empieza el núcleo, como múltiplo de la suma de los radios envolventes."""

    core_exponent: float
    """`n`: qué tan empinado sube el núcleo al acercarse."""


@dataclass(frozen=True, kw_only=True)
class SeekSpec:
    """Patrón: una aceleración de largo constante hacia el jugador, como una gravedad que
    apunta hacia él."""

    kind: Literal["seek"] = "seek"

    strength: float
    """Largo de la aceleración, en unidades / s². Con roce `γ`, la rapidez terminal es
    `strength / γ`."""


@dataclass(frozen=True, kw_only=True)
class CoulombSpec:
    """Patrón: el enemigo siente la ley de `charges`, de los otros enemigos y del
    jugador. No tiene números propios."""

    kind: Literal["coulomb"] = "coulomb"


type PatternSpec = SeekSpec | CoulombSpec
"""Un patrón de movimiento. En el JSON, su campo `kind` dice cuál es."""


@dataclass(frozen=True)
class EnemySpec:
    """Un tipo de enemigo: un polígono regular hecho de líneas, que se mueve por sus
    patrones (ADR 0020 y 0021)."""

    sides: int
    """Líneas al aparecer. Cada bala quita la que golpea y, sin líneas, muere."""

    radius: float
    """Radio del polígono, en unidades del plano: el del círculo que pasa por sus
    vértices. Es también su círculo envolvente, y no cambia al perder líneas."""

    speed: float
    """Velocidad máxima, en unidades del plano por segundo."""

    friction: float
    """Roce `γ`, en 1/s: resta `γ·v` a la aceleración. Sin roce, se desliza para
    siempre."""

    charge_per_line: float
    """Carga de cada línea. Su carga es esto por las líneas que le quedan, y su masa,
    las líneas que le quedan."""

    patterns: tuple[PatternSpec, ...]
    """Su conducta: los patrones de movimiento, cuyas aceleraciones se suman."""


@dataclass(frozen=True)
class SpawningSpec:
    """Cómo aparecen los enemigos."""

    distance: float
    """Distancia al jugador a la que aparecen, en unidades del plano. Tiene que quedar
    fuera de la vista: más que la esquina de la pantalla, más el radio del enemigo."""

    interval: float
    """Segundos entre una aparición y la siguiente. El primero aparece al empezar."""


@dataclass(frozen=True)
class PointWeaponSpec:
    """El arma punto: balas que salen del jugador hacia el centro del enemigo más cercano
    y avanzan en línea recta, `p(t) = p₀ + v·t`."""

    cooldown: float
    """Segundos entre un disparo y el siguiente."""

    speed: float
    """Rapidez de la bala, en unidades del plano por segundo."""

    range: float
    """Distancia que recorre la bala antes de desaparecer, en unidades del plano."""


@dataclass(frozen=True)
class Balance:
    """Todas las entidades del juego."""

    player: PlayerSpec
    """El jugador."""

    charges: ChargesSpec
    """La ley de cargas entre enemigos y con el jugador."""

    enemies: dict[str, EnemySpec]
    """Los tipos de enemigo, por nombre."""

    spawning: SpawningSpec
    """Cómo aparecen los enemigos."""

    point_weapon: PointWeaponSpec
    """El arma punto."""


# >>> datos (lo genera poe balance-importar)
BALANCE = Balance(
    player=PlayerSpec(speed=240.0, radius=12.0, charge=-14.0),
    charges=ChargesSpec(
        k=171000.0,
        cutoff=150.0,
        softening=1.0,
        player_softening=24.0,
        core_strength=20000.0,
        core_reach=1.2,
        core_exponent=8.0,
    ),
    enemies={
        "hexagon": EnemySpec(
            sides=6,
            radius=24.0,
            speed=120.0,
            friction=2.0,
            charge_per_line=1.0,
            patterns=(
                SeekSpec(kind="seek", strength=240.0),
                CoulombSpec(kind="coulomb"),
            ),
        )
    },
    spawning=SpawningSpec(distance=800.0, interval=2.0),
    point_weapon=PointWeaponSpec(cooldown=0.6, speed=300.0, range=700.0),
)
# <<< datos
