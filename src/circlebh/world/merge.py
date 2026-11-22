"""La fusión: cinco estrellas vivas se juntan en la gran estrella roja (spec de la 0.2.0,
decisiones 37 a 41).

La gran estrella aparece centrada en el jugador, así que el jugador queda dentro de la
figura. Para que nunca aparezca tocándolo, su línea más cercana al centro tiene que
quedar más lejos que el radio del jugador. En `{n/s}`, la línea de salto `s` es una
cuerda que abarca el ángulo `2πs/n`, y su distancia al centro es `R·cos(πs/n)`: la más
cercana es la del mayor `s`.
"""

import math
from collections.abc import Mapping
from enum import Enum, auto

from pygame.math import Vector2

from circlebh.balance import Balance, EnemySpec, MergeSpec
from circlebh.world.director import bar_at
from circlebh.world.enemy import Enemy


def beat_at(steps: int, bpm: float) -> float:
    """El pulso en que va la partida tras `steps` pasos: un compás son 4 pulsos. Sale
    del mismo reloj que los compases del director (ADR 0025)."""
    return 4 * bar_at(steps, bpm)


class MergeState(Enum):
    """En qué va la fusión."""

    CALM = auto()
    """No hay gran estrella. Las estrellas nacen."""
    WARNING = auto()
    """Las estrellas se juntaron, y el aviso titila encima del jugador."""
    PRESENT = auto()
    """La gran estrella está en el plano: mata y se golpea."""
    FADING = auto()
    """El jugador salió: se apaga, ya fuera del plano."""


class Merge:
    """La fusión de las estrellas en la gran estrella, un paso a la vez.

    Cuenta los pulsos con el tempo del director, así que el aviso cae en el pulso de la
    música sin que el mundo dependa de ella (ADR 0022).
    """

    def __init__(
        self, spec: MergeSpec, enemies: Mapping[str, EnemySpec], bpm: float
    ) -> None:
        self.spec = spec
        self.member = enemies[spec.enemy]
        """El tipo que se junta."""
        self.into = enemies[spec.into]
        """El tipo en que se juntan."""
        self.bpm = bpm
        self.state = MergeState.CALM
        self.present: Enemy | None = None
        """La gran estrella mientras está en el plano."""
        self.fading: Enemy | None = None
        """La gran estrella mientras se apaga, ya fuera del plano."""
        self._first_beat = 0
        """El primer pulso entero del aviso."""
        self._fade_start = 0.0
        """El pulso en que empezó a apagarse."""

    def allows(self, name: str) -> bool:
        """Si el tipo `name` puede nacer: fuera de la calma, no nacen estrellas."""
        return name != self.spec.enemy or self.state is MergeState.CALM

    def update(self, steps: int, enemies: list[Enemy], player: Vector2) -> list[Enemy]:
        """Avanza la fusión al paso `steps` y devuelve la lista nueva de enemigos.

        - En calma, si hay `count` estrellas vivas, se quitan sin morir y empieza el
          aviso en el pulso entero siguiente.
        - Tras `beats` pulsos de aviso, la gran estrella nace donde está el jugador.
        - Presente, si murió vuelve la calma. Si el jugador queda a más de
          `release · radius` de su centro, sale del plano y se apaga.
        - Tras `fade_beats` pulsos apagándose, vuelve la calma.
        """
        beat = beat_at(steps, self.bpm)
        if self.state is MergeState.CALM:
            members = [e for e in enemies if e.spec == self.member]
            if len(members) >= self.spec.count:
                enemies = [e for e in enemies if e.spec != self.member]
                self._first_beat = math.floor(beat) + 1
                self.state = MergeState.WARNING
        elif self.state is MergeState.WARNING:
            if beat >= self._first_beat + self.spec.beats:
                self.present = Enemy(self.into, Vector2(player))
                enemies = [*enemies, self.present]
                self.state = MergeState.PRESENT
        elif self.state is MergeState.PRESENT:
            present = self.present
            if present is None or not any(e is present for e in enemies):
                self.present = None
                self.state = MergeState.CALM
            elif player.distance_to(present.position) > (
                self.spec.release * present.radius
            ):
                enemies = [e for e in enemies if e is not present]
                self.present, self.fading = None, present
                self._fade_start = beat
                self.state = MergeState.FADING
        elif beat >= self._fade_start + self.spec.fade_beats:
            self.fading = None
            self.state = MergeState.CALM
        return enemies

    def blink(self, steps: int) -> bool:
        """Si el aviso se ve en el paso `steps`: en la primera mitad de cada uno de sus
        `beats` pulsos."""
        if self.state is not MergeState.WARNING:
            return False
        beat = beat_at(steps, self.bpm)
        within = self._first_beat <= beat < self._first_beat + self.spec.beats
        return within and beat % 1 < 0.5

    def fade(self, steps: int) -> float:
        """Cuánto queda de la gran estrella que se apaga: de 1 al empezar a 0 al final."""
        if self.state is not MergeState.FADING:
            return 0.0
        elapsed = beat_at(steps, self.bpm) - self._fade_start
        return max(0.0, 1.0 - elapsed / self.spec.fade_beats)


def check_merge(balance: Balance) -> None:
    """Rechaza al crear el mundo una fusión con tipos que no existen, o cuya figura
    tocaría al jugador al aparecer centrada en él."""
    spec, enemies = balance.merge, balance.enemies
    for field, name in (("enemy", spec.enemy), ("into", spec.into)):
        if name not in enemies:
            raise ValueError(f"merge.{field}: no existe el enemigo {name}")
    into = enemies[spec.into]
    shape = into.shape
    nearest = into.radius * math.cos(math.pi * max(shape.steps) / shape.vertices)
    if nearest <= balance.player.radius:
        raise ValueError(
            f"merge.into: su línea más cercana al centro queda a {nearest:.1f}, y"
            f" tocaría al jugador de radio {balance.player.radius}"
        )
