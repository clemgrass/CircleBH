"""El director: la partida sigue la forma de un tema (ADR 0025).

Cuenta compases con el tempo del balance y recorre las secciones del tema: intro,
subida, drop, respiro, subida y drop. Cada sección gana presupuesto de amenaza y lo
gasta comprando enemigos de su mazo, al azar por peso, con la `Random` del mundo.

Los drops son oleadas: compran todo al empezar, y el tema no sigue hasta que el jugador
las limpia (decisión 72 de la spec de la 0.2.0).
"""

import bisect
import itertools
import math
import random
from collections.abc import Mapping
from dataclasses import dataclass, replace

from circlebh.balance import DirectorSpec, EnemySpec, SectionSpec, SpawningSpec
from circlebh.world.clock import STEP
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
    for section in spec.sections:
        where = f"director.sections[{section.name}]"
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
            if wave and enemies[entry.enemy].anchored:
                raise ValueError(
                    f"{where}.deck[{entry.enemy}]: una oleada no puede tener"
                    " anclados, porque no te siguen y quizás nunca se limpie"
                )
            if entry.weight <= 0:
                raise ValueError(
                    f"{where}.deck[{entry.enemy}].weight: tiene que ser mayor que 0"
                )
            if enemies[entry.enemy].threat <= 0:
                raise ValueError(
                    f"enemies.{entry.enemy}.threat: tiene que ser mayor que 0"
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

    def section_at(self, bar: float) -> SectionSpec:
        """La sección del compás `bar`. Antes del compás 0 es la primera, y después del
        final, la última, que sigue."""
        return self.spec.sections[self._index_at(bar)]

    def _index_at(self, bar: float) -> int:
        last = len(self.spec.sections) - 1
        return max(0, min(bisect.bisect_right(self._starts, bar) - 1, last))

    def update(self, steps: int, *, wave_alive: bool) -> list[Purchase]:
        """Avanza hasta el paso `steps` y devuelve lo comprado en este paso.

        `wave_alive` dice si queda algún enemigo de la oleada en curso, vivo o en la
        cola. Fuera de una oleada no se usa.

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
        if self.section.kind == "build":
            bought += self._buy(bar - self._starts[self.section_index], closing=False)
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
        la sección siguiente sonaría como el drop durante toda su primera frase."""
        own_end = self._starts[self.section_index] + self.section.bars
        phrase = PHRASE_BARS * math.ceil((bar + 1) / PHRASE_BARS)
        self._start_next_at(max(own_end, phrase))
        self._waiting = False

    def _start_next_at(self, bar: float) -> None:
        """Corre las secciones que siguen a la actual para que la próxima empiece en el
        compás `bar`, con infinito si todavía no se sabe."""
        rest = self.spec.sections[self.section_index + 1 :]
        self._starts[self.section_index + 1 :] = itertools.accumulate(
            (s.bars for s in rest), initial=bar
        )

    def _buy(self, bars: float, *, closing: bool) -> list[Purchase]:
        """Compra mientras lo ganado en `bars` compases de la sección alcance para la
        compra que espera. Elegirla antes de tener con qué pagarla es lo que deja
        entrar a los caros: si se eligiera solo entre lo que alcanza, el presupuesto se
        iría siempre en lo más barato.

        Una formación se compra entera (decisión 28). Solo al cerrar la sección se
        recorta a lo que alcance, para no perder lo que queda.
        """
        available = earned(self.section, bars) - self._spent
        bought: list[Purchase] = []
        while self._next is not None:
            wanted = self._next
            cost = self.enemies[wanted.enemy].threat
            count = min(wanted.count, math.floor(available / cost))
            if count == 0 or (count < wanted.count and not closing):
                break
            bought.append(replace(wanted, count=count))
            self._spent += count * cost
            available -= count * cost
            # Al cerrar, la última de estas compras no se paga: `update` la reemplaza
            # por una de la sección nueva. Gasta un sorteo, pero la partida sigue igual
            # de repetible con la misma semilla.
            self._next = self._pick()
        return bought

    def _pick(self) -> Purchase | None:
        """La próxima compra: el tipo al azar por peso, la formación al azar entre las
        de la sección, y su tamaño entre `spawning.formation_size`. Sin mazo, ninguna.

        Un tipo `solitary` sale siempre `single` (decisión 45). Su formación se sortea
        igual y se descarta, para que el azar que sigue no dependa de qué tipo salió."""
        section = self.section
        if not section.deck:
            return None
        names = [entry.enemy for entry in section.deck]
        weights = [entry.weight for entry in section.deck]
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
