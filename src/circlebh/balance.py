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


@dataclass(frozen=True, kw_only=True)
class OrbitSpec:
    """Patrón: un resorte que lo lleva a distancia `radius` del jugador, y un empuje que
    lo hace girar a su alrededor. En polares desde el jugador:

    `a = −stiffness·(r − R)·r̂ + tangential·θ̂`.
    """

    kind: Literal["orbit"] = "orbit"

    radius: float
    """`R`: la distancia al jugador a la que tira el resorte, en unidades del plano."""

    stiffness: float
    """La rigidez del resorte, en 1/s². Con roce `γ`, oscila amortiguado si
    `γ² < 4·stiffness`."""

    tangential: float
    """El empuje tangencial, en unidades / s², antihorario si es positivo. Con 0, solo
    mantiene la distancia."""


type PatternSpec = SeekSpec | CoulombSpec | OrbitSpec
"""Un patrón de movimiento. En el JSON, su campo `kind` dice cuál es."""


@dataclass(frozen=True, kw_only=True)
class ChargeSpec:
    """Acción: la embestida. Te mira siempre con una punta, salvo al embestir. Si te ve
    con la recta libre, avisa retrocediendo como un resorte, se suelta hacia donde estás,
    embiste en línea recta sin corregir el rumbo y se recupera (`world/actions.py`)."""

    kind: Literal["charge"] = "charge"

    watch_distance: float
    """Solo avisa si el jugador está a esta distancia o menos. Tiene que caber en la
    vista, para que nadie embista desde fuera de la pantalla."""

    telegraph: float
    """Cuánto dura el aviso, en segundos. Te sigue mirando, y la dirección se elige al
    terminarlo."""

    recoil: float
    """Cuánto retrocede durante el aviso, alejándose de ti, en unidades del plano."""

    speed: float
    """La rapidez de la embestida, en unidades del plano por segundo. Pasa el tope
    `EnemySpec.speed`."""

    duration: float
    """Cuánto dura la embestida, en segundos."""

    cooldown: float
    """Cuánto se recupera después, en segundos, antes de volver a observar."""

    turn_rate: float
    """Lo más rápido que gira para mirarte, en rad/s. Como `spin`, cumple
    `turn_rate · STEP ≤ 0,1` (ADR 0027)."""

    lead_chance: float
    """La probabilidad de que una embestida salga desviada, de 0 a 1."""

    lead_angle: float
    """Cuánto se desvía, en radianes, hacia el lado con menos enemigos cerca de ti:
    adivina hacia dónde vas a escapar."""


@dataclass(frozen=True, kw_only=True)
class VolleySpec:
    """Acción: la ráfaga. Si te ve a distancia, avisa congelando su giro, y dispara
    `shots` salvas, una bala por vértice, mientras gira. Cada punta deja un brazo de la
    espiral de Arquímedes `r = (v/ω)·θ`. Después se recupera (`world/actions.py`)."""

    kind: Literal["volley"] = "volley"

    min_distance: float
    """No dispara con el jugador más cerca que esto: una bala que nace encima no se
    puede esquivar."""

    max_distance: float
    """Solo dispara con el jugador a esta distancia o menos. Tiene que caber en la
    vista, para que nadie dispare desde fuera de la pantalla."""

    telegraph: float
    """Cuánto dura el aviso, en segundos. Mientras avisa no gira: sus puntas muestran
    hacia dónde van a salir las balas."""

    shots: int
    """Cuántas salvas dispara en una ráfaga."""

    interval: float
    """Los segundos entre una salva y la siguiente."""

    cooldown: float
    """Cuánto se recupera después de la ráfaga, en segundos, antes de volver a mirar."""


@dataclass(frozen=True, kw_only=True)
class StarPolygonShape:
    """La figura de un enemigo: el polígono estrellado `{n/s}` (`world/figures.py`).

    Tiene `vertices` vértices en un círculo, y cada `s` de `steps` une el vértice `k`
    con el `k + s`. El hexágono es `{6/1}`, y la estrella, `{5/1}` más `{5/2}`: sus
    lados y sus diagonales."""

    kind: Literal["star_polygon"] = "star_polygon"

    vertices: int
    """Los vértices `n`, repartidos en el círculo del radio del enemigo."""

    steps: tuple[int, ...]
    """Los saltos `s`, cada uno con `1 ≤ s < n/2`. Con `(1,)`, es un polígono regular."""

    @property
    def line_count(self) -> int:
        """Las líneas de la figura entera: `n` por cada salto."""
        return self.vertices * len(self.steps)


type ActionSpec = ChargeSpec | VolleySpec
"""Una acción: lo que el enemigo hace y no es una fuerza (ADR 0021). En el JSON, su
campo `kind` dice cuál es."""


@dataclass(frozen=True)
class EnemySpec:
    """Un tipo de enemigo: una figura hecha de líneas, que se mueve por sus patrones
    (ADR 0020 y 0021)."""

    shape: StarPolygonShape
    """Su figura. Aparece con todas sus líneas: cada bala quita la que golpea y, sin
    líneas, muere."""

    radius: float
    """Radio de la figura, en unidades del plano: el del círculo que pasa por sus
    vértices. Es también su círculo envolvente."""

    speed: float
    """Velocidad máxima, en unidades del plano por segundo."""

    friction: float
    """Roce `γ`, en 1/s: resta `γ·v` a la aceleración. Sin roce, se desliza para
    siempre."""

    spin: float
    """Su velocidad angular al aparecer, `ω` en rad/s, antihoraria si es positiva. Con
    0 no gira. No es un patrón: los patrones son aceleraciones lineales (ADR 0027)."""

    anchored: bool
    """Si está anclado, como la estrella: nada lo mueve, ni sus patrones, ni las
    fuerzas, ni la red de seguridad. Tampoco gira, aunque tenga `spin`. Los demás lo
    sienten igual por Coulomb y por el núcleo duro."""

    charge_per_line: float
    """Carga de cada línea. Su carga es esto por las líneas que le quedan, y su masa,
    las líneas que le quedan."""

    patterns: tuple[PatternSpec, ...]
    """Su conducta: los patrones de movimiento, cuyas aceleraciones se suman."""

    threat: float
    """Su amenaza: lo que le cuesta al director comprarlo (ADR 0025)."""

    actions: tuple[ActionSpec, ...]
    """Sus acciones, como la embestida. Mientras una está activa, puede apagar sus
    patrones."""


@dataclass(frozen=True)
class SpawningSpec:
    """Cómo aparecen los enemigos."""

    distance: float
    """Distancia al jugador a la que aparecen, en unidades del plano. Tiene que quedar
    fuera de la vista: más que la esquina de la pantalla, más el radio del enemigo."""

    max_per_step: int
    """Cuántos enemigos salen de la cola, como mucho, en un paso. Reparte una oleada
    grande en varios pasos, fuera de la vista."""

    formation_gap: float
    """El espacio libre entre dos vecinos de una formación, más allá del alcance del
    núcleo duro (`charges.core_reach`). En unidades del plano."""

    formation_size: tuple[int, int]
    """El menor y el mayor tamaño de una formación que no es `single`."""


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
    """Las formaciones que puede usar: `single`, `ring`, `line` o `cluster`
    (`world/spawning.py`). Con mazo, al menos una."""


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
class EnemyBulletSpec:
    """Las balas enemigas: puntos que van en línea recta, `p(t) = p₀ + v·t`. Atraviesan
    a los enemigos sin tocarlos, matan al jugador y se borran al pasar
    `spawning.distance` de él (`world/enemy_bullets.py`)."""

    speed: float
    """Su rapidez, en unidades del plano por segundo. Más que la del jugador: no se las
    deja atrás corriendo, hay que esquivarlas."""

    radius: float
    """Su radio, en unidades del plano. Tocan al jugador a `player.radius + radius` de
    su centro, y se dibujan de este tamaño."""


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

    enemy_bullet: EnemyBulletSpec
    """Las balas que disparan los enemigos."""


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
            shape=StarPolygonShape(kind="star_polygon", vertices=6, steps=(1,)),
            radius=24.0,
            speed=120.0,
            friction=2.0,
            spin=0.0,
            anchored=False,
            charge_per_line=1.0,
            patterns=(
                SeekSpec(kind="seek", strength=240.0),
                CoulombSpec(kind="coulomb"),
            ),
            threat=1.0,
            actions=(),
        ),
        "square": EnemySpec(
            shape=StarPolygonShape(kind="star_polygon", vertices=4, steps=(1,)),
            radius=20.0,
            speed=120.0,
            friction=2.0,
            spin=1.5,
            anchored=False,
            charge_per_line=1.0,
            patterns=(
                SeekSpec(kind="seek", strength=240.0),
                CoulombSpec(kind="coulomb"),
            ),
            threat=1.0,
            actions=(),
        ),
        "triangle": EnemySpec(
            shape=StarPolygonShape(kind="star_polygon", vertices=3, steps=(1,)),
            radius=14.0,
            speed=150.0,
            friction=3.0,
            spin=0.0,
            anchored=False,
            charge_per_line=1.0,
            patterns=(
                OrbitSpec(kind="orbit", radius=280.0, stiffness=4.0, tangential=0.0),
                CoulombSpec(kind="coulomb"),
            ),
            threat=1.5,
            actions=(
                ChargeSpec(
                    kind="charge",
                    watch_distance=320.0,
                    telegraph=0.5,
                    recoil=14.0,
                    speed=720.0,
                    duration=0.8,
                    cooldown=2.0,
                    turn_rate=6.0,
                    lead_chance=0.1,
                    lead_angle=0.3,
                ),
            ),
        ),
        "pentagon": EnemySpec(
            shape=StarPolygonShape(kind="star_polygon", vertices=5, steps=(1,)),
            radius=22.0,
            speed=100.0,
            friction=2.0,
            spin=1.0,
            anchored=False,
            charge_per_line=1.0,
            patterns=(
                OrbitSpec(kind="orbit", radius=300.0, stiffness=6.0, tangential=0.0),
                CoulombSpec(kind="coulomb"),
            ),
            threat=2.0,
            actions=(
                VolleySpec(
                    kind="volley",
                    min_distance=120.0,
                    max_distance=320.0,
                    telegraph=0.6,
                    shots=4,
                    interval=0.15,
                    cooldown=2.5,
                ),
            ),
        ),
        "star": EnemySpec(
            shape=StarPolygonShape(kind="star_polygon", vertices=5, steps=(1, 2)),
            radius=40.0,
            speed=0.0,
            friction=0.0,
            spin=0.0,
            anchored=True,
            charge_per_line=0.6,
            patterns=(),
            threat=2.0,
            actions=(),
        ),
    },
    spawning=SpawningSpec(
        distance=800.0, max_per_step=4, formation_gap=20.0, formation_size=(3, 6)
    ),
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
                deck=(
                    DeckEntry(enemy="hexagon", weight=1.0),
                    DeckEntry(enemy="square", weight=1.0),
                ),
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
                deck=(
                    DeckEntry(enemy="hexagon", weight=1.0),
                    DeckEntry(enemy="square", weight=1.0),
                    DeckEntry(enemy="triangle", weight=1.0),
                ),
                formations=("single", "line"),
            ),
            SectionSpec(
                name="drop_1",
                kind="build",
                bars=32.0,
                budget_start=2.5,
                budget_end=2.5,
                burst=12.0,
                layers=(3, 3),
                deck=(
                    DeckEntry(enemy="hexagon", weight=1.0),
                    DeckEntry(enemy="square", weight=1.0),
                    DeckEntry(enemy="triangle", weight=1.0),
                ),
                formations=("ring", "line", "cluster"),
            ),
            SectionSpec(
                name="respiro",
                kind="build",
                bars=24.0,
                budget_start=0.5,
                budget_end=0.5,
                burst=0.0,
                layers=(0, 1),
                deck=(
                    DeckEntry(enemy="hexagon", weight=1.0),
                    DeckEntry(enemy="square", weight=1.0),
                    DeckEntry(enemy="triangle", weight=1.0),
                    DeckEntry(enemy="pentagon", weight=1.0),
                    DeckEntry(enemy="star", weight=0.5),
                ),
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
                deck=(
                    DeckEntry(enemy="hexagon", weight=1.0),
                    DeckEntry(enemy="square", weight=1.0),
                    DeckEntry(enemy="triangle", weight=1.0),
                    DeckEntry(enemy="pentagon", weight=1.0),
                    DeckEntry(enemy="star", weight=0.5),
                ),
                formations=("single", "line", "cluster"),
            ),
            SectionSpec(
                name="drop_2",
                kind="build",
                bars=32.0,
                budget_start=3.0,
                budget_end=3.0,
                burst=20.0,
                layers=(3, 3),
                deck=(
                    DeckEntry(enemy="hexagon", weight=1.0),
                    DeckEntry(enemy="square", weight=1.0),
                    DeckEntry(enemy="triangle", weight=1.0),
                    DeckEntry(enemy="pentagon", weight=1.0),
                ),
                formations=("ring", "line", "cluster"),
            ),
        ),
    ),
    point_weapon=PointWeaponSpec(cooldown=0.6, speed=300.0, range=700.0),
    enemy_bullet=EnemyBulletSpec(speed=330.0, radius=4.0),
)
# <<< datos
