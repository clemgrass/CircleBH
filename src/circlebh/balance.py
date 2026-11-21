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

    threat: float
    """Su amenaza: lo que le cuesta al director comprarlo (ADR 0025)."""


@dataclass(frozen=True)
class SpawningSpec:
    """Cómo aparecen los enemigos."""

    distance: float
    """Distancia al jugador a la que aparecen, en unidades del plano. Tiene que quedar
    fuera de la vista: más que la esquina de la pantalla, más el radio del enemigo."""


@dataclass(frozen=True)
class DeckEntry:
    """Un tipo de enemigo en el mazo de una sección."""

    enemy: str
    """El nombre del tipo, una clave de `enemies`."""

    weight: float
    """Su peso al sortear: con pesos 1 y 3, el segundo sale tres veces más."""


@dataclass(frozen=True)
class SectionSpec:
    """Una sección del tema: intro, subida, drop o respiro (ADR 0025)."""

    name: str
    """Su nombre, para el registro de la demo."""

    kind: Literal["build", "wave"]
    """`build` compra de a poco a lo largo de sus compases. `wave` es la oleada de un
    drop, que hay que limpiar; por ahora se comporta como `build`."""

    bars: float
    """Su largo, en compases. La última sección sigue después de ellos."""

    budget_start: float
    """El presupuesto al empezar, en amenaza por compás."""

    budget_end: float
    """El presupuesto al terminar, en amenaza por compás. Entre los dos, la tasa cambia
    de forma lineal, y lo que gana la sección es su integral."""

    burst: float
    """La ráfaga: amenaza que la sección compra entera en su primer paso, aparte de la
    tasa. Es lo que llueve justo después del golpe de un drop."""

    layers: tuple[int, int]
    """La capa mínima y la máxima de la música en esta sección, de 0 a 3 (ADR 0026).
    Dentro de ese rango, la intensidad elige."""

    deck: tuple[DeckEntry, ...]
    """Los tipos que puede comprar, con sus pesos. Sin mazo, no compra."""

    formations: tuple[str, ...]
    """Las formaciones que puede usar. Por ahora solo hay `single`."""


@dataclass(frozen=True)
class DirectorSpec:
    """El director: la forma del tema que sigue la partida (ADR 0025)."""

    bpm: float
    """El tempo, en pulsos por minuto. Un compás son 4 pulsos. La música lo lee de aquí."""

    max_alive: int
    """El tope de cuerpos vivos del modo infinito. Es provisorio, hasta medir con
    `poe benchmark` cuántos cuerpos caben en 16,6 ms por paso."""

    sections: tuple[SectionSpec, ...]
    """Las secciones, en orden."""


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

    director: DirectorSpec
    """La forma del tema: cuándo y qué se compra."""

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
        core_strength=30000.0,
        core_reach=1.2,
        core_exponent=4.0,
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
            threat=1.0,
        )
    },
    spawning=SpawningSpec(distance=800.0),
    director=DirectorSpec(
        bpm=124.0,
        max_alive=300,
        sections=(
            SectionSpec(
                name="intro",
                kind="build",
                bars=24.0,
                budget_start=0.5,
                budget_end=1.0,
                burst=0.0,
                layers=(0, 3),
                deck=(DeckEntry(enemy="hexagon", weight=1.0),),
                formations=("single",),
            ),
            SectionSpec(
                name="subida",
                kind="build",
                bars=24.0,
                budget_start=1.0,
                budget_end=2.0,
                burst=0.0,
                layers=(1, 3),
                deck=(DeckEntry(enemy="hexagon", weight=1.0),),
                formations=("single",),
            ),
            SectionSpec(
                name="drop_1",
                kind="build",
                bars=32.0,
                budget_start=2.5,
                budget_end=2.5,
                burst=12.0,
                layers=(3, 3),
                deck=(DeckEntry(enemy="hexagon", weight=1.0),),
                formations=("single",),
            ),
            SectionSpec(
                name="respiro",
                kind="build",
                bars=24.0,
                budget_start=0.5,
                budget_end=0.5,
                burst=0.0,
                layers=(0, 1),
                deck=(DeckEntry(enemy="hexagon", weight=1.0),),
                formations=("single",),
            ),
            SectionSpec(
                name="subida_2",
                kind="build",
                bars=16.0,
                budget_start=1.0,
                budget_end=2.5,
                burst=0.0,
                layers=(1, 3),
                deck=(DeckEntry(enemy="hexagon", weight=1.0),),
                formations=("single",),
            ),
            SectionSpec(
                name="drop_2",
                kind="build",
                bars=32.0,
                budget_start=3.0,
                budget_end=3.0,
                burst=20.0,
                layers=(3, 3),
                deck=(DeckEntry(enemy="hexagon", weight=1.0),),
                formations=("single",),
            ),
        ),
    ),
    point_weapon=PointWeaponSpec(cooldown=0.6, speed=300.0, range=700.0),
)
# <<< datos
