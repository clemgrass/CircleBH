"""La intensidad de la partida y la capa de la base (ADR 0022).

Con pocos enemigos la música se calma; con muchos y cerca, sube. La capa va de 0 (calma:
pad, sin bombo) a 3 (todo), y solo cambia al empezar una frase, como en el techno.
"""

import math
from collections.abc import Sequence
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

type Cue = Literal["riser", "impact"]
"""Un sonido que marca un cambio: el riser anuncia la subida, y el impacto la marca."""


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

    def advance(self, raw: float, g: int, seconds: float) -> list[Cue]:
        """Avanza a la semicorchea `g`, que dura `seconds`, con la intensidad cruda `raw`.

        Al empezar el último compás de una frase decide la capa de la siguiente, y si
        sube, suena un riser. Al empezar la frase siguiente, cambia, con un impacto si
        sube. Devuelve los sonidos que marcan el cambio.
        """
        target = 1 - math.exp(-raw / SCALE)
        tau = RISE_TAU if target > self.smooth else FALL_TAU
        self.smooth += (target - self.smooth) * min(1.0, seconds / tau)
        bar, sixteenth = divmod(g, SIXTEENTHS)
        cues: list[Cue] = []
        if sixteenth != 0:
            return cues
        if bar % PHRASE_BARS == PHRASE_BARS - 1:
            self._target = sum(self.smooth > threshold for threshold in THRESHOLDS)
            if self._target > self.level:
                cues.append("riser")
        elif bar % PHRASE_BARS == 0 and self._target != self.level:
            if self._target > self.level:
                cues.append("impact")
            self.level = self._target
        return cues

    def reset(self) -> list[Cue]:
        """Vuelve a la calma de golpe, con un impacto: una partida nueva o perdida."""
        self.level = self._target = 0
        self.smooth = 0.0
        return ["impact"]

    def rising(self, g: int) -> bool:
        """Si en el compás de `g` se viene una subida: el bombo calla en su último pulso."""
        bar = g // SIXTEENTHS
        return bar % PHRASE_BARS == PHRASE_BARS - 1 and self._target > self.level
