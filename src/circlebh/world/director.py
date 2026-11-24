"""El director: la partida sigue la forma de un tema (ADR 0025).

Cuenta compases con el tempo del balance y recorre las secciones del tema: intro,
subida, drop, respiro, subida y drop. Cada sección gana presupuesto de amenaza y lo
gasta comprando enemigos de su mazo, al azar por peso, con la `Random` del mundo.

Los drops son oleadas: compran todo al empezar, y el tema no sigue hasta que el jugador
las limpia (decisión 72 de la spec de la 0.2.0). Después del último drop viene el modo
infinito: su presupuesto crece de forma exponencial, compra cuerpos bajo un tope y, con
el tope lleno, sube el peligro (decisiones 20, 73 y 74).
"""

import bisect
import itertools
import math
import random
from collections.abc import Mapping
from dataclasses import dataclass, replace

from circlebh.balance import (
    DirectorSpec,
    EnemySpec,
    SectionSpec,
    SpawningSpec,
    StarPolygonShape,
)
from circlebh.world.clock import STEP
from circlebh.world.danger import NEUTRAL, Danger, danger_at
from circlebh.world.spawning import FORMATIONS, check_spawning

STEPS_PER_MINUTE = round(60 / STEP)
"""3600. Es entero, y así el compás se calcula sin el error binario de `1/60`."""

PHRASE_BARS = 4
"""Compases por frase. La música cambia de capa solo al empezar una frase (ADR 0026),
así que cada sección tiene que empezar en una."""


def bar_at(steps: int, bpm: float) -> float:
    """El compás en que va la partida tras `steps` pasos: `pasos · STEP · bpm / 240`.

    Se calcula desde el total de pasos, nunca sumando de a uno, para que el error no se
    acumule. El producto `steps · bpm` es exacto, y una sola división lo redondea.
    """
    return steps * bpm / (4 * STEPS_PER_MINUTE)


def earned(section: SectionSpec, bars: float) -> float:
    """Lo que ganó `section` en sus primeros `bars` compases.

    La ráfaga, `burst`, está entera desde el compás 0. Además, la tasa va de
    `budget_start` a `budget_end` en línea recta, así que se suma el área bajo esa
    recta. Pasados sus compases, sigue con la tasa del final.
    """
    start, end, length = section.budget_start, section.budget_end, section.bars
    x = min(bars, length)
    area = start * x + (end - start) * x * x / (2 * length)
    return section.burst + area + end * max(0.0, bars - length)


def endless_earned(bars: float, base: float, doubling: float) -> float:
    """Lo que ganó el infinito en sus primeros `bars` compases.

    La tasa es `B₀·2^(x/T)`, y lo ganado, su integral: `B₀·T/ln 2·(2^(x/T) − 1)`. Se
    calcula desde el compás, sin sumar de a uno, igual que `earned`.
    """
    return base * doubling / math.log(2) * (2 ** (bars / doubling) - 1)


def body_weight(spec: EnemySpec, enemies: Mapping[str, EnemySpec]) -> int:
    """Cuántos cuerpos puede llegar a ser un enemigo, para el tope del infinito.

    Uno que se parte al morir cuenta por lo que deja: el polígono de `n` lados suelta
    `n − 2` fragmentos, y cada uno cuenta por lo suyo. Se detiene ante un tipo
    desconocido o un ciclo, que `check_splits` rechaza al crear el mundo."""
    weight = 1
    seen: set[str] = set()
    while (
        spec.split_into in enemies
        and spec.split_into not in seen
        and isinstance(spec.shape, StarPolygonShape)
    ):
        seen.add(spec.split_into)
        weight *= spec.shape.vertices - 2
        spec = enemies[spec.split_into]
    return weight


def deck_weights(
    section: SectionSpec, enemies: Mapping[str, EnemySpec], sides: float
) -> list[float]:
    """Los pesos del mazo de `section`, cargados hacia los de más lados.

    Cada peso se multiplica por `(n/3)^(sides − 1)`, con `n` los vértices de su figura:
    con `sides = 1` quedan tal cual, y con 2, el octágono sale `8/3` veces más que un
    triángulo del mismo peso."""
    if sides == 1:
        return [entry.weight for entry in section.deck]
    weights = []
    for entry in section.deck:
        vertices = _vertices(enemies[entry.enemy])
        assert vertices is not None, "_validate lo exige en el infinito"
        weights.append(entry.weight * (vertices / 3) ** (sides - 1))
    return weights


def _vertices(spec: EnemySpec) -> int | None:
    """Los vértices de su figura, o `None` si no tiene, como el círculo."""
    return spec.shape.vertices if isinstance(spec.shape, StarPolygonShape) else None


def start_from(spec: DirectorSpec, section: str) -> DirectorSpec:
    """El tema desde la sección `section`, que empieza en el compás 0. Con `""`, el
    tema entero. Es para el desarrollo (`debug.start_section`, decisión 75)."""
    if not section:
        return spec
    names = [s.name for s in spec.sections]
    if section not in names:
        raise ValueError(
            f"debug.start_section: no existe la sección {section!r} en el tema"
            f" ({', '.join(names)})"
        )
    return replace(spec, sections=spec.sections[names.index(section) :])


@dataclass(frozen=True)
class Purchase:
    """Una compra del director: `count` enemigos de un tipo, en una formación."""

    enemy: str
    """El tipo, una clave de `enemies`."""

    formation: str
    """Una de `spawning.FORMATIONS`."""

    count: int
    """Cuántos. Siempre 1 en `single`."""

    wave: int | None = None
    """El índice de la sección `wave` que la compró, o `None` si no es de una oleada."""


def _split_chain(name: str, enemies: Mapping[str, EnemySpec]) -> list[str]:
    """`name` y todo lo que deja al morir, siguiendo `split_into`: lo que hay que
    matar para limpiar a uno de la oleada. Se detiene ante un tipo desconocido o un
    ciclo, que `check_splits` rechaza al crear el mundo."""
    chain: list[str] = []
    while name in enemies and name not in chain:
        chain.append(name)
        name = enemies[name].split_into
    return chain


def _validate(
    spec: DirectorSpec, enemies: Mapping[str, EnemySpec], spawning: SpawningSpec
) -> None:
    """Rechaza un tema que colgaría o rompería la partida a mitad de camino.

    Con amenaza 0 el director compraría sin fin en un solo paso; sin compases, `earned`
    dividiría por 0; y un tipo o una formación desconocidos, o un peso no positivo,
    fallarían recién al llegar a esa sección. Una oleada con tasa no la usaría, y una
    con un anclado podría no limpiarse nunca (Foco 4). Mejor fallar al empezar,
    nombrando el campo.
    """
    check_spawning(spawning)
    if not spec.sections:
        raise ValueError("director.sections: el tema necesita al menos una sección")
    _validate_endless(spec)
    for index, section in enumerate(spec.sections):
        where = f"director.sections[{section.name}]"
        if section.kind == "endless":
            _validate_endless_section(section, where, index, spec, enemies, spawning)
        if section.bars <= 0:
            raise ValueError(f"{where}.bars: tiene que ser mayor que 0")
        if section.deck and not section.formations:
            raise ValueError(f"{where}.formations: con mazo, necesita al menos una")
        for formation in section.formations:
            if formation not in FORMATIONS:
                raise ValueError(f"{where}.formations: no existe {formation}")
        wave = section.kind == "wave"
        for field in ("budget_start", "budget_end"):
            if wave and getattr(section, field) != 0:
                raise ValueError(
                    f"{where}.{field}: una oleada compra solo su burst al empezar,"
                    " así que su tasa tiene que ser 0"
                )
        for entry in section.deck:
            if entry.enemy not in enemies:
                raise ValueError(f"{where}.deck: no existe el enemigo {entry.enemy}")
            chain = _split_chain(entry.enemy, enemies) if wave else []
            anchored = next((n for n in chain if enemies[n].anchored), None)
            if anchored is not None:
                raise ValueError(
                    f"{where}.deck[{entry.enemy}]: una oleada no puede tener"
                    f" anclados ({anchored}), porque no te siguen y quizás nunca se"
                    " limpie"
                )
            if entry.weight <= 0:
                raise ValueError(
                    f"{where}.deck[{entry.enemy}].weight: tiene que ser mayor que 0"
                )
            if enemies[entry.enemy].threat <= 0:
                raise ValueError(
                    f"enemies.{entry.enemy}.threat: tiene que ser mayor que 0"
                )


def _validate_endless(spec: DirectorSpec) -> None:
    """Rechaza un infinito que no crece (`doubling ≤ 0`), un peligro que bajaría
    (`step < 0`) o un tope que lo achicaría (`< 1`)."""
    endless = spec.endless
    if endless.doubling <= 0:
        raise ValueError("director.endless.doubling: tiene que ser mayor que 0")
    if endless.step < 0:
        raise ValueError("director.endless.step: no puede ser negativo")
    for field in ("speed_cap", "cadence_cap", "sides_cap"):
        if getattr(endless, field) < 1:
            raise ValueError(f"director.endless.{field}: tiene que ser al menos 1")


def _validate_endless_section(
    section: SectionSpec,
    where: str,
    index: int,
    spec: DirectorSpec,
    enemies: Mapping[str, EnemySpec],
    spawning: SpawningSpec,
) -> None:
    """Rechaza una sección `endless` que no se podría jugar.

    El infinito sigue para siempre, así que va al final, y hay uno solo. Sin mazo o sin
    presupuesto no compraría nada; `budget_end` y `burst` no se usarían. Cada tipo
    necesita vértices para el peso de los lados, y su formación más grande tiene que
    caber bajo el tope: si no, esperaría para siempre."""
    if index != len(spec.sections) - 1:
        raise ValueError(
            f"{where}.kind: el infinito sigue para siempre, así que tiene que ser la"
            " última sección, y la única de su tipo"
        )
    if not section.deck:
        raise ValueError(f"{where}.deck: el infinito necesita al menos un tipo")
    if section.budget_start <= 0:
        raise ValueError(f"{where}.budget_start: es B₀, y tiene que ser mayor que 0")
    for field in ("budget_end", "burst"):
        if getattr(section, field) != 0:
            raise ValueError(f"{where}.{field}: el infinito no lo usa, tiene que ser 0")
    for entry in section.deck:
        enemy = enemies.get(entry.enemy)
        if enemy is None:
            continue  # El chequeo de todo mazo lo nombra.
        if _vertices(enemy) is None:
            raise ValueError(
                f"{where}.deck[{entry.enemy}]: el peso de los lados necesita una"
                " figura con vértices"
            )
        single = section.formations == ("single",) or enemy.solitary
        size = 1 if single else spawning.formation_size[1]
        if size * body_weight(enemy, enemies) > spec.max_alive:
            raise ValueError(
                f"director.max_alive: una formación de {size} {entry.enemy} no cabe"
                f" bajo el tope de {spec.max_alive} cuerpos, y el infinito la"
                " esperaría para siempre"
            )


class Director:
    """Recorre el tema y decide qué se compra en cada paso."""

    def __init__(
        self,
        spec: DirectorSpec,
        enemies: Mapping[str, EnemySpec],
        spawning: SpawningSpec,
        rng: random.Random,
    ) -> None:
        _validate(spec, enemies, spawning)
        self.spec = spec
        self.enemies = enemies
        self.spawning = spawning
        self.rng = rng
        self._starts = list(
            itertools.accumulate((s.bars for s in spec.sections), initial=0.0)
        )
        """El compás en que empieza cada sección, y al final, en que termina la última.
        Una oleada corre los de las que siguen: a infinito mientras espera, y a su final
        cuando se limpia."""
        self.section_index = 0
        self._entered = -1
        """La última sección que ya hizo lo de su primer paso: una oleada compra ahí."""
        self._waiting = False
        self._spent = 0.0
        self._excess = 0.0
        """Lo que el infinito ganó y no pudo gastar por el tope. Nunca baja."""
        self._weights = {name: body_weight(e, enemies) for name, e in enemies.items()}
        """Cuántos cuerpos cuenta cada tipo para el tope."""
        self._next = self._pick()

    @property
    def section(self) -> SectionSpec:
        """La sección en que va la partida."""
        return self.spec.sections[self.section_index]

    @property
    def waiting(self) -> bool:
        """Si espera que el jugador limpie la oleada en curso. Es verdadero desde el
        paso en que la oleada compra hasta el paso en que se limpia."""
        return self._waiting

    @property
    def excess(self) -> float:
        """Lo que el infinito ganó y no pudo gastar porque el tope estaba lleno."""
        return self._excess

    @property
    def danger(self) -> Danger:
        """El peligro con que nacen los enemigos en este paso: el que compra el
        excedente en el infinito, y el neutro fuera de él."""
        section = self.section
        if section.kind != "endless":
            return NEUTRAL
        return danger_at(self._excess, section.budget_start, self.spec.endless)

    def section_at(self, bar: float) -> SectionSpec:
        """La sección del compás `bar`. Antes del compás 0 es la primera, y después del
        final, la última, que sigue."""
        return self.spec.sections[self._index_at(bar)]

    def _index_at(self, bar: float) -> int:
        last = len(self.spec.sections) - 1
        return max(0, min(bisect.bisect_right(self._starts, bar) - 1, last))

    def update(self, steps: int, *, wave_alive: bool, bodies: int) -> list[Purchase]:
        """Avanza hasta el paso `steps` y devuelve lo comprado en este paso.

        `wave_alive` dice si queda algún enemigo de la oleada en curso, vivo o en la
        cola. Fuera de una oleada no se usa. `bodies` son los cuerpos que cuentan para el
        tope del infinito, y fuera de él tampoco se usa.

        Si en este paso empieza otra sección, la que termina gasta antes lo que le queda
        hasta su último compás, y la compra que esperaba se recorta a lo que alcance. Lo
        que no alcanza ni para uno se pierde. Una oleada no gasta al terminar: lo que le
        sobró se pierde.
        """
        bar = bar_at(steps, self.spec.bpm)
        if self._waiting and not wave_alive:
            self._clear(bar)
        bought: list[Purchase] = []
        while True:
            if self._entered < self.section_index:
                self._entered = self.section_index
                if self.section.kind == "wave":
                    bought += self._open_wave()
            if self.section_index >= self._index_at(bar):
                break
            if self.section.kind == "build":
                bought += self._buy(self.section.bars, closing=True)
            self.section_index += 1
            self._spent = 0.0
            self._next = self._pick()
        if self.section.kind != "wave":
            bars = bar - self._starts[self.section_index]
            bought += self._buy(bars, closing=False, bodies=bodies)
        return bought

    def _open_wave(self) -> list[Purchase]:
        """Compra la oleada entera: su `burst`, recortando la última formación a lo que
        alcance. Si compró algo, espera, y las secciones siguientes quedan sin inicio
        hasta que se limpie.

        En este paso el mundo todavía no ve a nadie de la oleada, que recién entra a
        la cola: por eso no se mira `wave_alive` hasta el paso siguiente."""
        bought = self._buy(0.0, closing=True)
        self._waiting = bool(bought)
        if self._waiting:
            self._start_next_at(math.inf)
        return bought

    def _clear(self, bar: float) -> None:
        """La oleada se limpió en el compás `bar`. Termina en el primer inicio de frase
        que llegue a sus compases y que caiga al menos un compás después de `bar`.

        El compás de margen es para la música, que decide la frase siguiente al empezar
        su último compás (ADR 0026): si la oleada terminara en la frase que ya decidió,
        la sección siguiente sonaría como el drop durante toda su primera frase. Si la
        siguiente exige más capas, el margen suma una frase: la de la subida, que la
        música decide al empezarla."""
        index = self.section_index
        own_end = self._starts[index] + self.section.bars
        following = self.spec.sections[index + 1 : index + 2]
        rises = any(s.layers[0] > self.section.layers[0] for s in following)
        margin = 1 + (PHRASE_BARS if rises else 0)
        end = max(own_end, bar + margin)
        self._start_next_at(PHRASE_BARS * math.ceil(end / PHRASE_BARS))
        self._waiting = False

    def _start_next_at(self, bar: float) -> None:
        """Corre las secciones que siguen a la actual para que la próxima empiece en el
        compás `bar`, con infinito si todavía no se sabe."""
        rest = self.spec.sections[self.section_index + 1 :]
        self._starts[self.section_index + 1 :] = itertools.accumulate(
            (s.bars for s in rest), initial=bar
        )

    def _buy(self, bars: float, *, closing: bool, bodies: int = 0) -> list[Purchase]:
        """Compra mientras lo ganado en `bars` compases de la sección alcance para la
        compra que espera. Elegirla antes de tener con qué pagarla es lo que deja
        entrar a los caros: si se eligiera solo entre lo que alcanza, el presupuesto se
        iría siempre en lo más barato.

        Una formación se compra entera (decisión 28). Solo al cerrar la sección se
        recorta a lo que alcance, para no perder lo que queda.

        En el infinito, además, la compra tiene que caber bajo `max_alive`, contando los
        `bodies` que ya hay. Si no cabe, se guarda solo lo que cuesta, para pagarla
        apenas haya espacio, y el resto pasa al excedente, que sube el peligro.
        """
        endless = self.section.kind == "endless"
        available = self._earned(bars) - self._spent - self._excess
        bought: list[Purchase] = []
        while self._next is not None:
            wanted = self._next
            cost = self.enemies[wanted.enemy].threat
            count = min(wanted.count, math.floor(available / cost))
            if count == 0 or (count < wanted.count and not closing):
                break
            if endless:
                need = count * self._weights[wanted.enemy]
                if bodies + need > self.spec.max_alive:
                    self._excess += available - count * cost
                    break
                bodies += need
            bought.append(replace(wanted, count=count))
            self._spent += count * cost
            available -= count * cost
            # Al cerrar, la última de estas compras no se paga: `update` la reemplaza
            # por una de la sección nueva. Gasta un sorteo, pero la partida sigue igual
            # de repetible con la misma semilla.
            self._next = self._pick()
        return bought

    def _earned(self, bars: float) -> float:
        """Lo que ganó la sección en curso en sus primeros `bars` compases."""
        section = self.section
        if section.kind == "endless":
            doubling = self.spec.endless.doubling
            return endless_earned(bars, section.budget_start, doubling)
        return earned(section, bars)

    def _pick(self) -> Purchase | None:
        """La próxima compra: el tipo al azar por peso, la formación al azar entre las
        de la sección, y su tamaño entre `spawning.formation_size`. Sin mazo, ninguna.

        Un tipo `solitary` sale siempre `single` (decisión 45). Su formación se sortea
        igual y se descarta, para que el azar que sigue no dependa de qué tipo salió."""
        section = self.section
        if not section.deck:
            return None
        names = [entry.enemy for entry in section.deck]
        weights = deck_weights(section, self.enemies, self.danger.sides)
        enemy = self.rng.choices(names, weights)[0]
        formation = self.rng.choice(section.formations)
        count = (
            1
            if formation == "single"
            else self.rng.randint(*self.spawning.formation_size)
        )
        wave = self.section_index if section.kind == "wave" else None
        if self.enemies[enemy].solitary:
            return Purchase(enemy, "single", 1, wave)
        return Purchase(enemy, formation, count, wave)
