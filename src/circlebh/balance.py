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

    follow: bool
    """Si el roce se mide desde el jugador y no desde el suelo. Suma `friction·u`, con
    `u` la velocidad del jugador: el roce total queda `−friction·(v − u)`, y en el marco
    del jugador es la misma órbita que con él quieto. Sin esto, el resorte radial no
    arrastra a los que van a los costados y el anillo queda detrás de quien corre."""


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
class SpiralSpec:
    """Acción: la espiral del círculo. Cruza el centro de la masa crítica a
    `cross_speed`, atrayendo; da media vuelta alrededor del jugador a `carry_speed` y a
    `carry_radius`, llevándose a los que atrapó, y los suelta; y después te persigue en
    la espiral logarítmica `ṙ = −λr`, `θ̇ = ω`, mirando solo dónde estás, no cómo te
    mueves (`world/actions.py`, decisiones 53, 54 y 57)."""

    kind: Literal["spiral"] = "spiral"

    angular_speed: float
    """`ω`, en rad/s, antihorario si es positiva. No puede ser 0: caería recto."""

    decay: float
    """`λ`, en 1/s: el radio se multiplica por `e^(−λ)` cada segundo. Tiene que ser
    mayor que 0, o nunca se acercaría."""

    cross_speed: float
    """Su rapidez al cruzar la masa crítica, en unidades del plano por segundo. Más que
    la del jugador, para que alcance al grupo aunque el jugador se mueva."""

    carry_speed: float
    """Su rapidez en la media vuelta en que se lleva a los que atrapó al otro lado del
    jugador (decisión 57). Menos que la de ellos, para que alcancen a seguirlo."""

    carry_radius: float
    """A qué distancia del jugador da la media vuelta. Tiene que dejar a la bola de
    atrapados lejos de él."""


@dataclass(frozen=True, kw_only=True)
class RegenerateSpec:
    """Acción: el médico. Herido, recupera la línea que le falta de índice menor cada
    `interval`, y un golpe reinicia la cuenta (`world/actions.py`, decisiones 65 a 67
    de la spec de la 0.2.0)."""

    kind: Literal["regenerate"] = "regenerate"

    interval: float
    """Su cooldown, en segundos: cuánto espera desde el último golpe o la última línea
    recuperada."""

    stray: str
    """El tipo de la línea que suelta al donar, una clave de `enemies`: un segmento con
    `deliver`."""


@dataclass(frozen=True, kw_only=True)
class DeliverSpec:
    """Acción: la línea suelta va a su paciente, el herido al que la donó el médico. Si
    el paciente muere, frena por su roce y queda flotando (decisión 68 de la spec de la
    0.2.0)."""

    kind: Literal["deliver"] = "deliver"

    speed: float
    """Su rapidez hacia el paciente, en unidades del plano por segundo."""


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


@dataclass(frozen=True, kw_only=True)
class CircleShape:
    """La figura del círculo: una sola línea curva, el círculo del radio del enemigo.
    Choca como círculo, no por segmentos (spec de la 0.2.0, "El círculo")."""

    kind: Literal["circle"] = "circle"

    @property
    def line_count(self) -> int:
        """Una sola línea: muere de un golpe."""
        return 1


@dataclass(frozen=True, kw_only=True)
class SegmentShape:
    """La figura de la línea suelta que dona el regenerador: un solo segmento, el
    diámetro de largo `2·radius` sobre el eje x de su marco (decisión 68 de la spec de
    la 0.2.0)."""

    kind: Literal["segment"] = "segment"

    @property
    def line_count(self) -> int:
        """Una sola línea: muere de un golpe."""
        return 1


type Shape = StarPolygonShape | CircleShape | SegmentShape
"""La figura de un enemigo. En el JSON, su campo `kind` dice cuál es."""


type ActionSpec = ChargeSpec | VolleySpec | SpiralSpec | RegenerateSpec | DeliverSpec
"""Una acción: lo que el enemigo hace y no es una fuerza (ADR 0021). En el JSON, su
campo `kind` dice cuál es."""


@dataclass(frozen=True)
class EnemySpec:
    """Un tipo de enemigo: una figura hecha de líneas, que se mueve por sus patrones
    (ADR 0020 y 0021)."""

    shape: Shape
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

    phantom: bool
    """Si los enemigos lo atraviesan, como la gran estrella roja: no entra al paso del
    enjambre, ni a sus fuerzas ni a la red de seguridad, y el arma no le apunta. Las
    balas del jugador sí le quitan líneas, y sus líneas matan al jugador. Se dibuja con
    el acento: lo rojo no choca con los enemigos."""

    solitary: bool
    """Si aparece siempre solo: el director lo compra como `single`, aunque la sección
    sortee otra formación."""

    charge_per_line: float
    """Carga de cada línea. Su carga es esto por las líneas que le quedan."""

    mass_per_line: float
    """Masa de cada línea. Su masa es esto por las líneas que le quedan (ADR 0027). Vale
    1 en todos menos el círculo. Al círculo hoy no le cambia nada, porque su espiral
    impone su velocidad y no siente fuerzas; el campo queda porque lo decide el ADR
    0027."""

    patterns: tuple[PatternSpec, ...]
    """Su conducta: los patrones de movimiento, cuyas aceleraciones se suman."""

    threat: float
    """Su amenaza: lo que le cuesta al director comprarlo (ADR 0025)."""

    actions: tuple[ActionSpec, ...]
    """Sus acciones, como la embestida. Mientras una está activa, puede apagar sus
    patrones."""

    split_into: str
    """El tipo de enemigo en que se parte al morir, o `""`. Un polígono regular de `n`
    lados suelta `n − 2`, en los centroides de su triangulación (decisión 71 de la spec
    de la 0.2.0)."""


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

    kind: Literal["build", "wave", "endless"]
    """`build` compra de a poco a lo largo de sus compases. `wave` es la oleada de un
    drop: compra todo su `burst` al empezar, y el tema no sigue hasta que se limpia. Una
    `wave` no tiene tasa, y su mazo no tiene anclados. `endless` es el modo infinito, la
    última sección: su tasa crece como `budget_start · 2^(x/T)` (`EndlessSpec`), y no
    usa `budget_end`, `burst` ni `bars`."""

    bars: float
    """Su largo, en compases. La última sección sigue después de ellos. En una `wave`
    es el largo mínimo: dura al menos esto y, además, hasta que se limpia."""

    budget_start: float
    """El presupuesto al empezar, en amenaza por compás."""

    budget_end: float
    """El presupuesto al terminar, en amenaza por compás. Entre los dos, la tasa cambia
    de forma lineal, y lo que gana la sección es su integral."""

    burst: float
    """La ráfaga: amenaza que la sección compra entera en su primer paso, aparte de la
    tasa. Es lo que llueve justo después del golpe de un drop. En una `wave`, es la
    oleada entera."""

    layers: tuple[int, int]
    """La capa mínima y la máxima de la música en esta sección, de 0 a 3 (ADR 0026).
    Dentro de ese rango, la intensidad elige."""

    deck: tuple[DeckEntry, ...]
    """Los tipos que puede comprar, con sus pesos. Sin mazo, no compra."""

    formations: tuple[str, ...]
    """Las formaciones que puede usar: `single`, `ring`, `line` o `cluster`
    (`world/spawning.py`). Con mazo, al menos una."""


@dataclass(frozen=True)
class EndlessSpec:
    """El modo infinito: cómo crece su presupuesto y cuánto peligro compra el excedente
    sobre el tope de cuerpos (decisiones 20 y 74).

    Cada multiplicador vale `min(tope, 1 + step·ℓ)`, con `ℓ = log₂(1 + E/B₀)`: sube un
    escalón por cada vez que se duplica el excedente `E`."""

    doubling: float
    """`T`: cada cuántos compases se duplica el presupuesto."""

    step: float
    """Cuánto sube cada multiplicador por cada duplicación del excedente."""

    speed_cap: float
    """El tope del multiplicador de velocidad de los que persiguen."""

    cadence_cap: float
    """El tope del multiplicador de la cadencia de los ataques."""

    sides_cap: float
    """El tope del multiplicador que carga el mazo hacia los de más lados."""


@dataclass(frozen=True)
class DirectorSpec:
    """El director: la forma del tema que sigue la partida (ADR 0025)."""

    bpm: float
    """El tempo, en pulsos por minuto. Un compás son 4 pulsos. La música lo lee de aquí."""

    max_alive: int
    """El tope de cuerpos del modo infinito: los vivos y los de la cola, cada uno por los
    cuerpos que puede llegar a ser. Sale de medir con `poe benchmark` cuántos caben en
    16,6 ms por paso (decisión 73)."""

    sections: tuple[SectionSpec, ...]
    """Las secciones, en orden."""

    endless: EndlessSpec
    """Los números propios del modo infinito."""


@dataclass(frozen=True)
class MergeSpec:
    """La fusión: `count` enemigos `enemy` vivos a la vez se juntan en un `into`, que
    aparece encima del jugador tras un aviso al pulso de la música (`world/merge.py`)."""

    enemy: str
    """El tipo que se junta, una clave de `enemies`."""

    count: int
    """Cuántos vivos a la vez disparan la fusión."""

    into: str
    """El tipo en que se juntan, una clave de `enemies`. Aparece centrado en el jugador,
    y ninguna de sus líneas puede tocarlo."""

    beats: int
    """Los pulsos que titila el aviso. Aparece al empezar el pulso siguiente."""

    release: float
    """Se desvanece cuando el jugador queda a más de `release` radios de su centro."""

    fade_beats: float
    """Cuántos pulsos dura el desvanecerse. Mientras, ya no mata ni se golpea."""


@dataclass(frozen=True)
class CriticalMassSpec:
    """La masa crítica: con `count` enemigos o más, cargados hacia un lado del jugador,
    aparece un `enemy` que los reparte (`world/critical_mass.py`). No lo compra el
    director, y hay a lo más uno a la vez."""

    enemy: str
    """El tipo que aparece, una clave de `enemies`: el círculo."""

    count: int
    """Cuántos enemigos tiene que haber, sin contar anclados ni fantasmas."""

    imbalance: float
    """El mínimo de `R̄ = |Σ ûᵢ| / N`, entre 0 y 1: 0 si te rodean parejo, 1 si están
    todos del mismo lado."""

    cooldown_bars: float
    """Cuántos compases espera, después de que muere, antes de que pueda aparecer otro."""


@dataclass(frozen=True)
class AdvanceSpec:
    """El avance de un arma, `a(t)`, a lo largo de `û` o del radio (ADR 0029).

    Según el grado: `v·τ` con 0, `v·t` con 1 y `v·t²/(2τ)` con 2. `d/dt` baja un grado
    y `∫dt` lo sube.
    """

    coefficient: float
    """`v`, en unidades del plano por segundo. Con 0 no hay avance."""

    degree: int
    """0, 1 o 2."""


@dataclass(frozen=True)
class HarmonicSpec:
    """Un armónico, `A·sin(k·t + φ)`: desvía de lado en el marco cartesiano, y suma al
    radio en el polar (ADR 0029)."""

    amplitude: float
    """`A`, en unidades del plano."""

    k: float
    """`k`, en radianes por segundo."""

    phase: float
    """`φ`, en radianes."""


@dataclass(frozen=True)
class PayloadSpec:
    """Lo que viaja: el punto que dispara el arma (ADR 0029 y 0033)."""

    size: float
    """El radio del proyectil, en unidades del plano. Con 0, es un punto."""

    lines: int
    """Cuántas líneas quita un golpe."""

    pierce: int
    """A cuántos enemigos atraviesa un proyectil antes de desaparecer."""


@dataclass(frozen=True)
class WeaponSpec:
    """Un arma: una función del punto, con tres términos en un marco y sus operadores
    (ADR 0029 y 0033).

    La posición de lo que dispara es una función pura de este `spec` y del tiempo
    (`world/terms.py`). Mejorar el arma es reemplazar su `spec`.
    """

    title: str
    """Su nombre, como se muestra al jugador."""

    kind: Literal["projectile"]
    """Qué dispara. Todo ataque es un punto (ADR 0033)."""

    frame: Literal["cartesian", "polar"]
    """El marco, con el origen donde se disparó: cartesiano, o polar, en que el radio
    gira con `Ω`."""

    aim: Literal["nearest", "motion"]
    """Hacia dónde apunta `û`: al enemigo más cercano, con anticipación, o hacia donde
    se mueve el jugador."""

    advance: AdvanceSpec
    """El avance, `a(t)`."""

    harmonics: tuple[HarmonicSpec, ...]
    """Los armónicos, sumados."""

    spin: float
    """`Ω`, el giro en el marco polar, en radianes por segundo. 0 si no gira."""

    copies: int
    """`Cₙ`: cuántas copias rotadas `2π/n`. 1 es solo el arma."""

    mirror: bool
    """Si suma una copia reflejada respecto de `û`."""

    parallel: float
    """La paralela: dos copias a `±d` por la normal. 0 si no hay."""

    payload: PayloadSpec
    """Lo que viaja."""

    cooldown: float
    """Segundos entre un disparo y el siguiente."""

    reach: float
    """El alcance: el punto desaparece cuando su avance llega aquí, en unidades del
    plano."""

    tau: float
    """`τ`, en segundos: la constante de `d/dt` y `∫dt`, que deja las unidades en largo."""


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
class RegrowSpec:
    """Las líneas que vuelven: nunca aparecen de golpe (decisión 66 de la spec de la
    0.2.0)."""

    fade: float
    """Cuánto dura el fundido de una línea que vuelve, en segundos, desde el color del
    fondo hasta el del trazo."""


@dataclass(frozen=True)
class ExperienceSpec:
    """La experiencia: el punto que deja cada enemigo al morir y lo que cuesta cada nivel
    (spec de la 0.3.0, decisiones 3 y 13).

    El punto es un cuerpo del plano sin choque, de masa 1. Siente la carga del jugador
    con la ley de cargas (ADR 0021), y no a los enemigos."""

    charge: float
    """La carga de cada punto, del signo de la de los enemigos: la del jugador lo atrae."""

    friction: float
    """`γ`: el roce del punto, en 1/s. Sin roce, un punto que pasa de largo orbitaría al
    jugador sin llegar nunca."""

    base: float
    """`a` en `a·nᵇ`: la experiencia que pide subir del nivel 1. Tiene que ser mayor que
    0."""

    exponent: float
    """`b` en `a·nᵇ`: cuánto más cuesta cada nivel que el anterior."""


@dataclass(frozen=True)
class KnobChange:
    """Una perilla: cambia un número del arma (ADR 0029, M1)."""

    kind: Literal["knob"]

    field: str
    """La ruta del campo en `WeaponSpec`, como `"cooldown"` o `"advance.coefficient"`."""

    op: Literal["add", "mul"]
    """Si el valor se suma o multiplica. Un campo entero queda entero, redondeado."""

    values: tuple[float, ...]
    """Los valores posibles. La mano elige uno con la `Random` del mundo."""


@dataclass(frozen=True)
class NewWeaponChange:
    """Un arma nueva: suma la `fₖ` que sigue, igual a la función base (ADR 0033)."""

    kind: Literal["weapon"]


@dataclass(frozen=True)
class PlayerChange:
    """Una mejora fuera del ataque: cambia al jugador o sus usos de reroll y banish."""

    kind: Literal["player"]

    field: Literal["speed", "radius", "charge", "rerolls", "banishes"]
    """Lo que cambia: un campo de `PlayerSpec`, o los usos que quedan."""

    op: Literal["add", "mul"]
    """Si el valor se suma o multiplica. Los usos quedan enteros, redondeados."""

    values: tuple[float, ...]
    """Los valores posibles. La mano elige uno con la `Random` del mundo."""


type CardChange = KnobChange | NewWeaponChange | PlayerChange
"""Lo que cambia una tarjeta, elegido por su `kind`."""


@dataclass(frozen=True)
class CardSpec:
    """Una tarjeta de la mano (spec de la 0.3.0, "La mano"). Solo entra a la mano si
    tiene efecto sobre lo que tienes."""

    title: str
    """El verbo del frente: la idea matemática, como "Acelerar el punto"."""

    symbol: str
    """El símbolo grande del frente, como `v × 1,25`."""

    family: Literal["knob", "term", "operator", "weapon", "player"]
    """El tipo que muestra el frente: perilla, suma, operador, arma nueva o jugador."""

    weapons: tuple[str, ...]
    """Las armas a las que sirve, de `"f1"` a `"f4"`. Vacío: a toda arma que tengas."""

    change: CardChange
    """Lo que cambia."""

    shape: bool
    """Si cambia la clase de forma del arma. La mano favorece a estas."""


@dataclass(frozen=True)
class LevelUpSpec:
    """Lo que pasa al subir de nivel (spec de la 0.3.0, "La mano")."""

    freeze_steps: int
    """Cuántos pasos más da el mundo después de llenar el nivel, antes de repartir. La
    escena los reparte en unos 0,4 s para que el juego frene."""

    hand_size: int
    """Cuántas tarjetas trae la mano."""

    max_weapons: int
    """Cuántas armas puedes tener a la vez."""

    rerolls: int
    """Cuántas veces puedes cambiar la mano entera, al empezar la partida."""

    banishes: int
    """Cuántas tarjetas puedes sacar de la partida, al empezar."""


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

    merge: MergeSpec
    """La fusión de las estrellas en la gran estrella roja."""

    critical_mass: CriticalMassSpec
    """Cuándo aparece el círculo que reparte al enjambre."""

    weapon: WeaponSpec
    """La función base, el punto: con ella parte `f₁`, y cada arma nueva (ADR 0033)."""

    enemy_bullet: EnemyBulletSpec
    """Las balas que disparan los enemigos."""

    regrow: RegrowSpec
    """Cómo vuelven las líneas."""

    experience: ExperienceSpec
    """La experiencia y los niveles."""

    level_up: LevelUpSpec
    """La mano al subir de nivel."""

    cards: dict[str, CardSpec]
    """Las tarjetas, por nombre."""


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
            phantom=False,
            solitary=False,
            charge_per_line=1.0,
            mass_per_line=1.0,
            patterns=(
                SeekSpec(kind="seek", strength=240.0),
                CoulombSpec(kind="coulomb"),
            ),
            threat=1.0,
            actions=(),
            split_into="",
        ),
        "square": EnemySpec(
            shape=StarPolygonShape(kind="star_polygon", vertices=4, steps=(1,)),
            radius=20.0,
            speed=120.0,
            friction=2.0,
            spin=1.5,
            anchored=False,
            phantom=False,
            solitary=False,
            charge_per_line=1.0,
            mass_per_line=1.0,
            patterns=(
                SeekSpec(kind="seek", strength=240.0),
                CoulombSpec(kind="coulomb"),
            ),
            threat=1.0,
            actions=(),
            split_into="",
        ),
        "triangle": EnemySpec(
            shape=StarPolygonShape(kind="star_polygon", vertices=3, steps=(1,)),
            radius=14.0,
            speed=150.0,
            friction=3.0,
            spin=0.0,
            anchored=False,
            phantom=False,
            solitary=False,
            charge_per_line=1.0,
            mass_per_line=1.0,
            patterns=(
                OrbitSpec(
                    kind="orbit",
                    radius=280.0,
                    stiffness=4.0,
                    tangential=0.0,
                    follow=False,
                ),
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
            split_into="",
        ),
        "pentagon": EnemySpec(
            shape=StarPolygonShape(kind="star_polygon", vertices=5, steps=(1,)),
            radius=22.0,
            speed=100.0,
            friction=2.0,
            spin=1.0,
            anchored=False,
            phantom=False,
            solitary=False,
            charge_per_line=1.0,
            mass_per_line=1.0,
            patterns=(
                OrbitSpec(
                    kind="orbit",
                    radius=300.0,
                    stiffness=6.0,
                    tangential=0.0,
                    follow=False,
                ),
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
            split_into="",
        ),
        "octagon": EnemySpec(
            shape=StarPolygonShape(kind="star_polygon", vertices=8, steps=(1,)),
            radius=26.0,
            speed=300.0,
            friction=4.0,
            spin=0.0,
            anchored=False,
            phantom=False,
            solitary=False,
            charge_per_line=1.0,
            mass_per_line=1.0,
            patterns=(
                OrbitSpec(
                    kind="orbit",
                    radius=200.0,
                    stiffness=12.0,
                    tangential=240.0,
                    follow=True,
                ),
                CoulombSpec(kind="coulomb"),
            ),
            threat=1.5,
            actions=(),
            split_into="",
        ),
        "magnet": EnemySpec(
            shape=StarPolygonShape(kind="star_polygon", vertices=6, steps=(2,)),
            radius=26.0,
            speed=120.0,
            friction=2.0,
            spin=0.0,
            anchored=False,
            phantom=False,
            solitary=True,
            charge_per_line=-2.0,
            mass_per_line=1.0,
            patterns=(
                SeekSpec(kind="seek", strength=240.0),
                CoulombSpec(kind="coulomb"),
            ),
            threat=2.0,
            actions=(),
            split_into="",
        ),
        "regenerator": EnemySpec(
            shape=StarPolygonShape(kind="star_polygon", vertices=7, steps=(3,)),
            radius=24.0,
            speed=120.0,
            friction=2.0,
            spin=0.0,
            anchored=False,
            phantom=False,
            solitary=True,
            charge_per_line=3.0,
            mass_per_line=1.0,
            patterns=(
                OrbitSpec(
                    kind="orbit",
                    radius=300.0,
                    stiffness=6.0,
                    tangential=0.0,
                    follow=False,
                ),
                CoulombSpec(kind="coulomb"),
            ),
            threat=3.0,
            actions=(
                RegenerateSpec(kind="regenerate", interval=2.0, stray="stray_line"),
            ),
            split_into="",
        ),
        "stray_line": EnemySpec(
            shape=SegmentShape(kind="segment"),
            radius=12.0,
            speed=200.0,
            friction=3.0,
            spin=0.0,
            anchored=False,
            phantom=False,
            solitary=True,
            charge_per_line=0.2,
            mass_per_line=1.0,
            patterns=(CoulombSpec(kind="coulomb"),),
            threat=0.0,
            actions=(DeliverSpec(kind="deliver", speed=180.0),),
            split_into="",
        ),
        "star": EnemySpec(
            shape=StarPolygonShape(kind="star_polygon", vertices=5, steps=(1, 2)),
            radius=40.0,
            speed=0.0,
            friction=0.0,
            spin=0.0,
            anchored=True,
            phantom=False,
            solitary=True,
            charge_per_line=0.6,
            mass_per_line=1.0,
            patterns=(),
            threat=2.0,
            actions=(),
            split_into="",
        ),
        "red_star": EnemySpec(
            shape=StarPolygonShape(kind="star_polygon", vertices=5, steps=(2,)),
            radius=150.0,
            speed=0.0,
            friction=0.0,
            spin=0.0,
            anchored=True,
            phantom=True,
            solitary=True,
            charge_per_line=0.0,
            mass_per_line=1.0,
            patterns=(),
            threat=0.0,
            actions=(),
            split_into="",
        ),
        "circle": EnemySpec(
            shape=CircleShape(kind="circle"),
            radius=8.0,
            speed=0.0,
            friction=0.0,
            spin=0.0,
            anchored=False,
            phantom=False,
            solitary=False,
            charge_per_line=60.0,
            mass_per_line=600.0,
            patterns=(),
            threat=0.0,
            actions=(
                SpiralSpec(
                    kind="spiral",
                    angular_speed=1.2,
                    decay=0.3,
                    cross_speed=360.0,
                    carry_speed=100.0,
                    carry_radius=250.0,
                ),
            ),
            split_into="",
        ),
        "divider": EnemySpec(
            shape=StarPolygonShape(kind="star_polygon", vertices=7, steps=(1,)),
            radius=36.0,
            speed=120.0,
            friction=2.0,
            spin=0.0,
            anchored=False,
            phantom=False,
            solitary=False,
            charge_per_line=1.0,
            mass_per_line=1.0,
            patterns=(
                SeekSpec(kind="seek", strength=240.0),
                CoulombSpec(kind="coulomb"),
            ),
            threat=2.5,
            actions=(),
            split_into="shard",
        ),
        "shard": EnemySpec(
            shape=StarPolygonShape(kind="star_polygon", vertices=3, steps=(1,)),
            radius=7.0,
            speed=150.0,
            friction=3.0,
            spin=0.0,
            anchored=False,
            phantom=False,
            solitary=False,
            charge_per_line=1.0,
            mass_per_line=1.0,
            patterns=(
                OrbitSpec(
                    kind="orbit",
                    radius=280.0,
                    stiffness=4.0,
                    tangential=0.0,
                    follow=False,
                ),
                CoulombSpec(kind="coulomb"),
            ),
            threat=0.0,
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
            split_into="",
        ),
    },
    spawning=SpawningSpec(
        distance=800.0, max_per_step=4, formation_gap=20.0, formation_size=(3, 6)
    ),
    director=DirectorSpec(
        bpm=124.0,
        max_alive=150,
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
                    DeckEntry(enemy="star", weight=0.25),
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
                    DeckEntry(enemy="star", weight=0.35),
                ),
                formations=("single", "line"),
            ),
            SectionSpec(
                name="drop_1",
                kind="wave",
                bars=8.0,
                budget_start=0.0,
                budget_end=0.0,
                burst=30.0,
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
                    DeckEntry(enemy="octagon", weight=1.0),
                    DeckEntry(enemy="magnet", weight=0.5),
                    DeckEntry(enemy="regenerator", weight=0.5),
                    DeckEntry(enemy="divider", weight=0.5),
                    DeckEntry(enemy="star", weight=0.5),
                ),
                formations=("single", "line", "cluster"),
            ),
            SectionSpec(
                name="drop_2",
                kind="wave",
                bars=8.0,
                budget_start=0.0,
                budget_end=0.0,
                burst=50.0,
                layers=(3, 3),
                deck=(
                    DeckEntry(enemy="hexagon", weight=1.0),
                    DeckEntry(enemy="square", weight=1.0),
                    DeckEntry(enemy="triangle", weight=1.0),
                    DeckEntry(enemy="pentagon", weight=1.0),
                    DeckEntry(enemy="octagon", weight=1.0),
                    DeckEntry(enemy="magnet", weight=0.5),
                    DeckEntry(enemy="regenerator", weight=0.5),
                    DeckEntry(enemy="divider", weight=0.5),
                ),
                formations=("ring", "line", "cluster"),
            ),
            SectionSpec(
                name="infinito",
                kind="endless",
                bars=4.0,
                budget_start=3.0,
                budget_end=0.0,
                burst=0.0,
                layers=(2, 3),
                deck=(
                    DeckEntry(enemy="hexagon", weight=1.0),
                    DeckEntry(enemy="square", weight=1.0),
                    DeckEntry(enemy="triangle", weight=1.0),
                    DeckEntry(enemy="pentagon", weight=1.0),
                    DeckEntry(enemy="octagon", weight=1.0),
                    DeckEntry(enemy="magnet", weight=0.5),
                    DeckEntry(enemy="regenerator", weight=0.5),
                    DeckEntry(enemy="divider", weight=0.5),
                    DeckEntry(enemy="star", weight=0.5),
                ),
                formations=("single", "ring", "line", "cluster"),
            ),
        ),
        endless=EndlessSpec(
            doubling=16.0, step=0.25, speed_cap=1.5, cadence_cap=2.0, sides_cap=2.0
        ),
    ),
    merge=MergeSpec(
        enemy="star", count=5, into="red_star", beats=3, release=1.5, fade_beats=1.0
    ),
    critical_mass=CriticalMassSpec(
        enemy="circle", count=30, imbalance=0.5, cooldown_bars=8.0
    ),
    weapon=WeaponSpec(
        title="Punto",
        kind="projectile",
        frame="cartesian",
        aim="nearest",
        advance=AdvanceSpec(coefficient=300.0, degree=1),
        harmonics=(),
        spin=0.0,
        copies=1,
        mirror=False,
        parallel=0.0,
        payload=PayloadSpec(size=0.0, lines=1, pierce=0),
        cooldown=0.6,
        reach=700.0,
        tau=0.5,
    ),
    enemy_bullet=EnemyBulletSpec(speed=330.0, radius=4.0),
    regrow=RegrowSpec(fade=0.4),
    experience=ExperienceSpec(charge=3.0, friction=3.0, base=6.0, exponent=1.5),
    level_up=LevelUpSpec(
        freeze_steps=12, hand_size=3, max_weapons=4, rerolls=1, banishes=1
    ),
    cards={
        "point_speed": CardSpec(
            title="Acelerar el punto",
            symbol="v × 1,25",
            family="knob",
            weapons=(),
            change=KnobChange(
                kind="knob", field="advance.coefficient", op="mul", values=(1.25,)
            ),
            shape=False,
        ),
        "point_cooldown": CardSpec(
            title="Disparar más seguido",
            symbol="cooldown × 0,8",
            family="knob",
            weapons=(),
            change=KnobChange(kind="knob", field="cooldown", op="mul", values=(0.8,)),
            shape=False,
        ),
        "player_speed": CardSpec(
            title="Moverte más rápido",
            symbol="speed × 1,1",
            family="player",
            weapons=(),
            change=PlayerChange(kind="player", field="speed", op="mul", values=(1.1,)),
            shape=False,
        ),
        "player_radius": CardSpec(
            title="Achicar tu círculo",
            symbol="r × 0,9",
            family="player",
            weapons=(),
            change=PlayerChange(kind="player", field="radius", op="mul", values=(0.9,)),
            shape=False,
        ),
        "player_charge": CardSpec(
            title="Cargarte más",
            symbol="q × 1,25",
            family="player",
            weapons=(),
            change=PlayerChange(
                kind="player", field="charge", op="mul", values=(1.25,)
            ),
            shape=False,
        ),
        "new_weapon": CardSpec(
            title="Sumar otro punto",
            symbol="+ f",
            family="weapon",
            weapons=(),
            change=NewWeaponChange(kind="weapon"),
            shape=True,
        ),
    },
)
# <<< datos
