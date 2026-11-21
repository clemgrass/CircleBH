"""Las acciones: lo que un enemigo hace y no es una fuerza (ADR 0021).

Los patrones suman aceleraciones. Una acción, en cambio, es una máquina de estados
chica, con sus tiempos en el balance. Puede apagar los patrones (`controls_motion`) y
fijar la velocidad (`velocity`) o el giro (`omega`) del enemigo.

Todas las acciones se actualizan antes del paso del enjambre, con las posiciones del
inicio del paso. Cada una cambia solo su propio estado. El orden de la lista importa
solo para lo que sacan de la `Random`, y es siempre el de aparición.
"""

import math
import random
from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum, auto
from typing import TYPE_CHECKING

from pygame.math import Vector2

from circlebh.balance import ActionSpec, ChargeSpec
from circlebh.world.clock import STEP
from circlebh.world.collisions import segment_touches_circle
from circlebh.world.events import Event, Telegraph
from circlebh.world.rigid import rotate

if TYPE_CHECKING:
    from circlebh.world.enemy import Enemy


@dataclass(frozen=True)
class ActionContext:
    """Lo que una acción puede mirar en este paso."""

    player_position: Vector2
    enemies: Sequence[Enemy]
    """Todos los enemigos vivos, también el que actúa."""
    rng: random.Random
    """La `Random` del mundo, el único azar de la partida (ADR 0005)."""


class Action(ABC):
    """La base de toda acción."""

    @abstractmethod
    def update(self, enemy: Enemy, context: ActionContext) -> list[Event]:
        """Avanza un paso la acción de `enemy`, y devuelve lo que pasó."""

    @property
    def controls_motion(self) -> bool:
        """Si apaga los patrones: el enemigo siente solo su roce."""
        return False

    @property
    def velocity(self) -> Vector2 | None:
        """La velocidad que la acción le fija al enemigo, sin tope, o `None`."""
        return None

    @property
    def omega(self) -> float | None:
        """La velocidad angular que la acción le fija al enemigo, o `None`: entonces
        gira con su `spin`."""
        return None


def steps_of(seconds: float) -> int:
    """Cuántos pasos dura una etapa de `seconds`. Se cuenta en pasos y no en segundos,
    para que restar `STEP` no acumule error."""
    return round(seconds / STEP)


def clear_line(
    start: Vector2, end: Vector2, radius: float, others: Sequence[Enemy]
) -> bool:
    """Si un cuerpo de `radius` puede ir en línea recta de `start` a `end` sin tocar el
    círculo envolvente de ninguno de `others`.

    Lo que barre el cuerpo es una cápsula: el tramo engordado en `radius`. Tocar un
    círculo de radio `ρ` con ella es lo mismo que tocar con el tramo un círculo de radio
    `ρ + radius` (la suma de Minkowski).
    """
    return not any(
        segment_touches_circle(start, end, other.position, other.radius + radius)
        for other in others
    )


class ChargeState(Enum):
    WATCHING = auto()
    """Lo mueven sus patrones, y busca la recta libre hasta el jugador."""
    TELEGRAPHING = auto()
    """Avisa: sigue mirando al jugador y retrocede, como un resorte que se comprime."""
    CHARGING = auto()
    """Embiste a `speed` en la dirección que eligió al soltarse, sin corregir el rumbo."""
    RECOVERING = auto()
    """Lo mueven sus patrones otra vez, pero todavía no puede avisar."""


class Charge(Action):
    """La embestida del triángulo: observa, avisa, embiste y se recupera.

    Te mira siempre con una punta, salvo al embestir. Solo avisa con el jugador a
    `watch_distance` o menos y con la recta libre. Al terminar el aviso se suelta hacia
    donde está el jugador, o, con probabilidad `lead_chance`, a `lead_angle` de él, hacia
    el lado con menos enemigos (decisión 30 de la spec de la 0.2.0). Si al soltarse la
    recta está tapada, no embiste y vuelve a observar.
    """

    def __init__(self, spec: ChargeSpec) -> None:
        self.spec = spec
        self.state = ChargeState.WATCHING
        self.direction = Vector2()
        """Hacia dónde embiste, unitaria. Se elige al soltarse."""
        self._durations = {
            ChargeState.TELEGRAPHING: steps_of(spec.telegraph),
            ChargeState.CHARGING: steps_of(spec.duration),
            ChargeState.RECOVERING: steps_of(spec.cooldown),
        }
        self._left = 0
        """Los pasos que le quedan a la etapa, contando el actual."""
        self._velocity: Vector2 | None = None
        self._omega: float | None = None

    @property
    def controls_motion(self) -> bool:
        return self.state in (ChargeState.TELEGRAPHING, ChargeState.CHARGING)

    @property
    def velocity(self) -> Vector2 | None:
        return self._velocity

    @property
    def omega(self) -> float | None:
        return self._omega

    def update(self, enemy: Enemy, context: ActionContext) -> list[Event]:
        events = self._advance(enemy, context)
        self._move(enemy, context)
        return events

    def _advance(self, enemy: Enemy, context: ActionContext) -> list[Event]:
        """Cuenta los pasos de la etapa y pasa a la siguiente cuando se acaban."""
        if self.state is not ChargeState.WATCHING:
            self._left -= 1
            if self._left > 0:
                return []
            if self.state is ChargeState.TELEGRAPHING:
                aim = self._launch(enemy, context)
                if aim is not None:
                    self.direction = aim
                    self._enter(ChargeState.CHARGING)
                    return []
                self._enter(ChargeState.WATCHING)
            elif self.state is ChargeState.CHARGING:
                self._enter(ChargeState.RECOVERING)
            else:
                self._enter(ChargeState.WATCHING)
        # Al terminar la recuperación, ya mira en este mismo paso.
        if self.state is ChargeState.WATCHING and self._sees(enemy, context):
            self._enter(ChargeState.TELEGRAPHING)
            return [Telegraph(enemy)]
        return []

    def _move(self, enemy: Enemy, context: ActionContext) -> None:
        """La velocidad y el giro que fija en este paso, según la etapa."""
        if self.state is ChargeState.CHARGING:
            self._velocity = self.direction * self.spec.speed
            self._omega = 0.0
            return
        to_player = context.player_position - enemy.position
        self._omega = self._turn(enemy.angle, to_player)
        if self.state is ChargeState.TELEGRAPHING and to_player.length_squared() > 0:
            self._velocity = -to_player.normalize() * self._recoil_speed()
        else:
            self._velocity = None

    def _turn(self, angle: float, to_player: Vector2) -> float:
        """La velocidad angular que lleva su primera punta hacia el jugador, a lo más
        `turn_rate`. Esa punta está en `π/2` del marco del enemigo (`polygon.py`), así
        que apunta al jugador con `θ = atan2(d) − π/2`. Gira por el lado más corto."""
        if to_player.length_squared() == 0:
            return 0.0
        target = math.atan2(to_player.y, to_player.x) - math.pi / 2
        turn = math.remainder(target - angle, math.tau) / STEP
        return max(-self.spec.turn_rate, min(self.spec.turn_rate, turn))

    def _recoil_speed(self) -> float:
        """La rapidez del retroceso en este paso del aviso.

        El retroceso sigue `x(s) = recoil · sen(π·s/2)`, con `s` de 0 a 1 a lo largo del
        aviso: rápido al empezar, y quieto justo antes de soltarse, como un resorte que
        se comprime. En el paso `k` de `n`, avanza `x((k+1)/n) − x(k/n)`, así que la suma
        de todos los pasos da `recoil` exacto.
        """
        n = self._durations[ChargeState.TELEGRAPHING]
        k = n - self._left

        def x(step: int) -> float:
            return self.spec.recoil * math.sin(math.pi / 2 * step / n)

        return (x(k + 1) - x(k)) / STEP

    def _launch(self, enemy: Enemy, context: ActionContext) -> Vector2 | None:
        """Hacia dónde se suelta, unitaria, o `None` si la recta al jugador está tapada.

        Con probabilidad `lead_chance` se desvía `lead_angle` hacia el lado con menos
        enemigos cerca del jugador. Si esa recta está tapada, va directo.
        """
        player = context.player_position
        to_player = player - enemy.position
        others = [other for other in context.enemies if other is not enemy]
        if to_player.length_squared() == 0 or not clear_line(
            enemy.position, player, enemy.radius, others
        ):
            return None
        direct = to_player.normalize()
        if context.rng.random() >= self.spec.lead_chance:
            return direct
        side = self._emptier_side(direct, player, others, context.rng)
        lead = rotate(direct, side * self.spec.lead_angle)
        end = enemy.position + lead * to_player.length()
        return lead if clear_line(enemy.position, end, enemy.radius, others) else direct

    def _emptier_side(
        self,
        direct: Vector2,
        player: Vector2,
        others: Sequence[Enemy],
        rng: random.Random,
    ) -> int:
        """`+1` si hay menos enemigos a la izquierda de `direct` (girar antihorario), y
        `−1` si hay menos a la derecha. Cuentan los que están a `watch_distance` o menos
        del jugador. El lado sale del signo de `direct × (p − jugador)`. Si empatan,
        decide `rng`."""
        left = right = 0
        for other in others:
            offset = other.position - player
            if offset.length() > self.spec.watch_distance:
                continue
            side = direct.cross(offset)
            left += side > 0
            right += side < 0
        if left == right:
            return rng.choice((-1, 1))
        return 1 if left < right else -1

    def _enter(self, state: ChargeState) -> None:
        self.state = state
        self._left = self._durations.get(state, 0)

    def _sees(self, enemy: Enemy, context: ActionContext) -> bool:
        """Si el jugador está a la vista y con la recta libre. Encima de él no hay
        dirección, y no avisa."""
        distance = enemy.position.distance_to(context.player_position)
        if distance == 0 or distance > self.spec.watch_distance:
            return False
        others = [other for other in context.enemies if other is not enemy]
        return clear_line(enemy.position, context.player_position, enemy.radius, others)


def make_action(spec: ActionSpec) -> Action:
    """La instancia de la acción que describe `spec`, nueva para cada enemigo."""
    match spec:
        case ChargeSpec():
            return Charge(spec)


def step_actions(
    enemies: Sequence[Enemy], player_position: Vector2, rng: random.Random
) -> list[Event]:
    """Avanza un paso las acciones de todos los enemigos vivos, y devuelve sus eventos.

    Van en el orden de la lista, que es el de aparición: así, lo que sacan de `rng` es
    siempre lo mismo con la misma semilla."""
    alive = [enemy for enemy in enemies if enemy.alive]
    context = ActionContext(Vector2(player_position), alive, rng)
    events: list[Event] = []
    for enemy in alive:
        for action in enemy.actions:
            events += action.update(enemy, context)
    return events
