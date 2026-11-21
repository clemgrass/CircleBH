"""Las acciones: lo que un enemigo hace y no es una fuerza (ADR 0021).

Los patrones suman aceleraciones. Una acción, en cambio, es una máquina de estados
chica, con sus tiempos en el balance. Mientras está activa, puede apagar los patrones
(`controls_motion`) y hasta fijar la velocidad del enemigo (`velocity`).

Todas las acciones se actualizan antes del paso del enjambre, con las posiciones del
inicio del paso. Cada una cambia solo su propio estado, así que el orden de la lista no
cambia el resultado.
"""

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

if TYPE_CHECKING:
    from circlebh.world.enemy import Enemy


@dataclass(frozen=True)
class ActionContext:
    """Lo que una acción puede mirar en este paso."""

    player_position: Vector2
    enemies: Sequence[Enemy]
    """Todos los enemigos vivos, también el que actúa."""


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
    """Avisa: la dirección ya está fija, y solo lo frena el roce."""
    CHARGING = auto()
    """Embiste a `speed` en la dirección fija, sin corregir el rumbo."""
    RECOVERING = auto()
    """Lo mueven sus patrones otra vez, pero todavía no puede avisar."""


NEXT_STATE = {
    ChargeState.TELEGRAPHING: ChargeState.CHARGING,
    ChargeState.CHARGING: ChargeState.RECOVERING,
    ChargeState.RECOVERING: ChargeState.WATCHING,
}


class Charge(Action):
    """La embestida del triángulo: observa, avisa, embiste y se recupera.

    Solo avisa con el jugador a `watch_distance` o menos y con la recta libre. Desde
    ahí, nada lo detiene: el aviso y la embestida duran lo que dice el balance.
    """

    def __init__(self, spec: ChargeSpec) -> None:
        self.spec = spec
        self.state = ChargeState.WATCHING
        self.direction = Vector2()
        """Hacia dónde embiste. Se fija al empezar el aviso, y es unitaria desde ahí."""
        self._durations = {
            ChargeState.TELEGRAPHING: steps_of(spec.telegraph),
            ChargeState.CHARGING: steps_of(spec.duration),
            ChargeState.RECOVERING: steps_of(spec.cooldown),
        }
        self._left = 0
        """Los pasos que le quedan a la etapa, contando el actual."""

    @property
    def controls_motion(self) -> bool:
        return self.state in (ChargeState.TELEGRAPHING, ChargeState.CHARGING)

    @property
    def velocity(self) -> Vector2 | None:
        if self.state is ChargeState.CHARGING:
            return self.direction * self.spec.speed
        return None

    @property
    def reach(self) -> float:
        """Lo que recorre la embestida entera: `speed · duration`."""
        return self.spec.speed * self.spec.duration

    def update(self, enemy: Enemy, context: ActionContext) -> list[Event]:
        if self.state is not ChargeState.WATCHING:
            self._left -= 1
            if self._left > 0:
                return []
            self._enter(NEXT_STATE[self.state])
        # Al terminar la recuperación, ya mira en este mismo paso.
        if self.state is ChargeState.WATCHING and self._sees(enemy, context):
            self.direction = (context.player_position - enemy.position).normalize()
            self._enter(ChargeState.TELEGRAPHING)
            return [Telegraph(enemy)]
        return []

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


def step_actions(enemies: Sequence[Enemy], player_position: Vector2) -> list[Event]:
    """Avanza un paso las acciones de todos los enemigos vivos, y devuelve sus eventos."""
    alive = [enemy for enemy in enemies if enemy.alive]
    context = ActionContext(Vector2(player_position), alive)
    events: list[Event] = []
    for enemy in alive:
        for action in enemy.actions:
            events += action.update(enemy, context)
    return events
