"""La intensidad de la partida y la capa de la base (ADR 0022 y 0026).

Con pocos enemigos la música se calma; con muchos y cerca, sube. La capa va de 0 (calma:
pad, sin bombo) a 3 (todo), y solo cambia al empezar una frase, como en el techno. Cada
sección del tema acota la capa, y antes de una sección que exige todo suena una subida.
"""

import math
from collections.abc import Callable, Sequence
from typing import Literal

from pygame.math import Vector2

from circlebh.audio.rhythm import SIXTEENTHS
from circlebh.world.enemy import Enemy

DISTANCE = 400.0
"""A esta distancia, un enemigo pesa 1/e de lo que pesa encima del jugador."""
SCALE = 3.0
"""La intensidad cruda que lleva la suavizada a 1 − 1/e."""
RISE_TAU = 1.0
FALL_TAU = 5.0
"""Segundos para recorrer ~63 % del camino al subir y al bajar: sube rápido, baja lento."""
THRESHOLDS = (0.08, 0.2, 0.38)
"""La intensidad suavizada que hay que pasar para cada capa, de la 1 a la 3."""
PHRASE_BARS = 4
"""Compases por frase."""
PHRASE = PHRASE_BARS * SIXTEENTHS
"""Semicorcheas por frase."""
TOP = 3
"""La capa más alta: todo suena."""
SILENT_SIXTEENTHS = 4
"""Las últimas semicorcheas de una subida, un pulso, en que la base calla."""

type Layers = tuple[int, int]
"""La capa mínima y la máxima que permite una sección (ADR 0026)."""
FREE: Layers = (0, TOP)
"""Sin sección que acote: manda la intensidad."""

type Cue = Literal["riser", "impact", "build"]
"""Un sonido que marca un cambio: el riser anuncia que la capa sube, el impacto lo
marca, y `build` empieza la subida de una frase antes de un drop."""


def _free(_bar: int) -> Layers:
    return FREE


def raw_intensity(enemies: Sequence[Enemy], player: Vector2) -> float:
    """`Σ (líneas que quedan / lados) · e^(−d/DISTANCE)`: cuánto aprieta la partida."""
    return sum(
        len(enemy.edges)
        / enemy.spec.sides
        * math.exp(-enemy.position.distance_to(player) / DISTANCE)
        for enemy in enemies
    )


class Arrangement:
    """La capa de la base y la intensidad suavizada, semicorchea a semicorchea."""

    def __init__(self) -> None:
        self.level = 0
        """La capa que suena, de 0 a 3."""
        self.smooth = 0.0
        """La intensidad suavizada, de 0 a 1."""
        self._target = 0
        """La capa decidida en el último compás de la frase."""
        self._ceiling = TOP
        """La capa máxima de la sección de la frase que suena."""
        self._build_from: int | None = None
        """La semicorchea en que empezó la subida de esta frase, si la hay."""

    def advance(
        self,
        raw: float,
        g: int,
        seconds: float,
        layers_at: Callable[[int], Layers] = _free,
    ) -> list[Cue]:
        """Avanza a la semicorchea `g`, que dura `seconds`, con la intensidad cruda `raw`.

        `g` cuenta desde que empezó la partida, así que las frases también, y
        `layers_at(bar)` da las capas que permite la sección del compás `bar`.

        Al empezar el último compás de una frase decide la capa de la siguiente: la de
        la intensidad, acotada por su sección. Si sube, suena un riser. Al empezar la
        frase siguiente, cambia, con un impacto si sube o si termina una subida. Si la
        frase que viene después exige todo y la de ahora no, esta frase es una subida.
        Devuelve los sonidos que marcan el cambio.
        """
        target = 1 - math.exp(-raw / SCALE)
        tau = RISE_TAU if target > self.smooth else FALL_TAU
        self.smooth += (target - self.smooth) * min(1.0, seconds / tau)
        bar, sixteenth = divmod(g, SIXTEENTHS)
        cues: list[Cue] = []
        if sixteenth != 0:
            return cues
        if bar % PHRASE_BARS == PHRASE_BARS - 1:
            low, high = layers_at(bar + 1)
            wanted = sum(self.smooth > threshold for threshold in THRESHOLDS)
            self._target = min(max(wanted, low), high)
            if self._target > self.level and not self.building(g):
                cues.append("riser")
        elif bar % PHRASE_BARS == 0:
            if self._target > self.level or self.building(g - 1):
                cues.append("impact")
            self.level = self._target
            now, self._ceiling = layers_at(bar)
            following, _ = layers_at(bar + PHRASE_BARS)
            self._build_from = g if following == TOP > now else None
            if self._build_from is not None:
                cues.append("build")
        return cues

    def building(self, g: int) -> bool:
        """Si la semicorchea `g` es parte de una subida."""
        start = self._build_from
        return start is not None and start <= g < start + PHRASE

    def silent(self, g: int) -> bool:
        """Si en la semicorchea `g` la base calla: el último pulso de una subida."""
        start = self._build_from
        if start is None or not self.building(g):
            return False
        return g - start >= PHRASE - SILENT_SIXTEENTHS

    @property
    def brightness(self) -> float:
        """Qué tan abierto va el filtro, de 0 a 1: lo que pida la intensidad o la capa,
        lo que sea mayor, con el techo de la sección. Así el drop suena brillante aunque
        haya pocos enemigos cerca, y el respiro suena apagado aunque haya muchos."""
        open_ = max(self.smooth, self.level / TOP)
        return min(open_, (self._ceiling + 1) / (TOP + 1))

    def reset(self) -> list[Cue]:
        """Vuelve a la calma de golpe, con un impacto: una partida nueva o perdida."""
        self.level = self._target = 0
        self.smooth = 0.0
        self._ceiling = TOP
        self._build_from = None
        return ["impact"]

    def rising(self, g: int) -> bool:
        """Si en el compás de `g` se viene una subida: el bombo calla en su último pulso."""
        bar = g // SIXTEENTHS
        return bar % PHRASE_BARS == PHRASE_BARS - 1 and self._target > self.level
