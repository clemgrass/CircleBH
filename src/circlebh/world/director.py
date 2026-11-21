"""El director: la partida sigue la forma de un tema (ADR 0025).

Cuenta compases con el tempo del balance y recorre las secciones del tema: intro,
subida, drop, respiro, subida y drop. Cada sección gana presupuesto de amenaza y lo
gasta comprando enemigos de su mazo, al azar por peso, con la `Random` del mundo.
"""

import bisect
import itertools
import random
from collections.abc import Mapping

from circlebh.balance import DirectorSpec, EnemySpec, SectionSpec
from circlebh.world.clock import STEP

STEPS_PER_MINUTE = round(60 / STEP)
"""3600. Es entero, y así el compás se calcula sin el error binario de `1/60`."""


def bar_at(steps: int, bpm: float) -> float:
    """El compás en que va la partida tras `steps` pasos: `pasos · STEP · bpm / 240`.

    Se calcula desde el total de pasos, nunca sumando de a uno, para que el error no se
    acumule. El producto `steps · bpm` es exacto, y una sola división lo redondea.
    """
    return steps * bpm / (4 * STEPS_PER_MINUTE)


def earned(section: SectionSpec, bars: float) -> float:
    """Lo que ganó `section` en sus primeros `bars` compases.

    La tasa va de `budget_start` a `budget_end`, en línea recta, así que lo ganado es el
    área bajo esa recta. Pasados sus compases, sigue con la tasa del final.
    """
    start, end, length = section.budget_start, section.budget_end, section.bars
    x = min(bars, length)
    area = start * x + (end - start) * x * x / (2 * length)
    return area + end * max(0.0, bars - length)


class Director:
    """Recorre el tema y decide qué se compra en cada paso."""

    def __init__(
        self,
        spec: DirectorSpec,
        enemies: Mapping[str, EnemySpec],
        rng: random.Random,
    ) -> None:
        self.spec = spec
        self.enemies = enemies
        self.rng = rng
        self._starts = list(
            itertools.accumulate((s.bars for s in spec.sections), initial=0.0)
        )
        """El compás en que empieza cada sección, y al final, en que termina la última."""
        self.section_index = 0
        self._spent = 0.0
        self._next = self._pick()

    @property
    def section(self) -> SectionSpec:
        """La sección en que va la partida."""
        return self.spec.sections[self.section_index]

    def update(self, steps: int) -> list[str]:
        """Avanza hasta el paso `steps` y devuelve los tipos comprados en este paso.

        Si en este paso empieza otra sección, la que termina gasta antes lo que le queda
        hasta su último compás. Lo que no alcanza para su próxima compra se pierde.
        """
        bar = bar_at(steps, self.spec.bpm)
        last = len(self.spec.sections) - 1
        index = min(bisect.bisect_right(self._starts, bar) - 1, last)
        bought: list[str] = []
        while self.section_index < index:
            bought += self._buy(self.section.bars)
            self.section_index += 1
            self._spent = 0.0
            self._next = self._pick()
        bought += self._buy(bar - self._starts[self.section_index])
        return bought

    def _buy(self, bars: float) -> list[str]:
        """Compra mientras lo ganado en `bars` compases de la sección alcance para la
        compra que espera. Elegirla antes de tener con qué pagarla es lo que deja
        entrar a los caros: si se eligiera solo entre lo que alcanza, el presupuesto se
        iría siempre en lo más barato."""
        available = earned(self.section, bars) - self._spent
        bought: list[str] = []
        while self._next is not None:
            cost = self.enemies[self._next].threat
            if cost > available:
                break
            bought.append(self._next)
            self._spent += cost
            available -= cost
            self._next = self._pick()
        return bought

    def _pick(self) -> str | None:
        """El tipo de la próxima compra, al azar por peso. Sin mazo, ninguno."""
        deck = self.section.deck
        if not deck:
            return None
        names = [entry.enemy for entry in deck]
        weights = [entry.weight for entry in deck]
        return self.rng.choices(names, weights)[0]
