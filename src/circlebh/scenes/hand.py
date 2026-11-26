"""La mano en la escena: el frenado, las tarjetas que suben y bajan, y la entrada
(spec de la 0.3.0, decisiones 7, 8 y 11).

El mundo decide cuándo hay mano y qué trae; aquí solo se reparte el tiempo y se anima:
- **El frenado:** los `freeze_steps` del mundo se reparten en el doble de pasos de
  escena, cada vez más espaciados (`slowdown_steps`). Con 12, son 0,4 s.
- **La mano:** las tarjetas suben al medio. ← → y A D se mueven, con vuelta; ↑ ↓ y W S
  dan vuelta la elegida, cada una hacia su lado; Enter elige. En el control, la cruceta
  y el stick hacen lo mismo, y el botón de abajo elige.
- **Al elegir,** bajan, y el juego retoma su velocidad.

Mientras la mano está abierta, la escena no avanza ni el mundo ni la música
(decisión 7): vuelven juntos, en sincronía.
"""

import random
from collections.abc import Callable
from dataclasses import replace

import pygame

from circlebh.controls import HandCommand, StickSteps, hand_command
from circlebh.pilot import pick_at_random
from circlebh.render.cards import CardPose, CardView, HandPose, card_views, draw_hand
from circlebh.render.palette import Palette
from circlebh.viewport import Viewport
from circlebh.world.cards import Offer
from circlebh.world.clock import STEP, slowdown_steps
from circlebh.world.game import World

RISE_STEPS = round(0.3 / STEP)
"""Cuánto tardan las tarjetas en subir: 0,3 s."""
FALL_STEPS = round(0.25 / STEP)
"""Cuánto tardan en bajar al elegir: 0,25 s."""
FLIP_STEPS = round(0.2 / STEP)
"""Cuánto tarda una tarjeta en darse vuelta: 0,2 s."""
DEMO_CHOOSE_STEPS = round(1.5 / STEP)
"""En la demo, cuánto se ve la mano antes de que el piloto elija: 1,5 s."""


class HandScene:
    """El frenado y la mano de una partida, en pantalla."""

    def __init__(
        self,
        *,
        demo: bool,
        chooser: random.Random,
        moves: tuple[tuple[float, HandCommand], ...] = (),
    ) -> None:
        """`chooser` es la `Random` propia con que la demo elige, sembrada con la
        semilla de la partida. `moves` son órdenes que la demo da en cada mano, a los
        segundos indicados desde que se abre: las usan las capturas."""
        self.demo = demo
        self.chooser = chooser
        self.moves = moves
        self.stick = StickSteps()
        self.selected = 0
        self._shown: tuple[Offer, ...] = ()
        """La mano que está dibujada. Si el mundo trae otra, se arma de nuevo."""
        self._views: list[CardView] = []
        self._cards: list[CardPose] = []
        self._open_steps = 0
        """Pasos de escena desde que se abrió la mano."""
        self._freeze_steps = 0
        """Pasos de escena desde que empezó el frenado."""
        self._leaving = 0
        """Pasos que les quedan a las tarjetas para terminar de bajar."""
        self._time = 0.0
        """Los segundos de la vista previa del arma."""

    def step(self, world: World, advance: Callable[[], None]) -> bool:
        """Un paso de escena. Llama a `advance` si el mundo tiene que dar un paso, y
        devuelve si lo dio: la música avanza solo con él."""
        self._leaving = max(0, self._leaving - 1)
        if world.hand:
            self._freeze_steps = 0
            self._lay_out(world)
            self._open_steps += 1
            self._time += STEP
            self._cards = [
                replace(card, flip=min(1.0, card.flip + 1 / FLIP_STEPS))
                for card in self._cards
            ]
            if self.demo:
                self._play_demo(world)
            return False
        if world.freezing > 0:
            self._freeze_steps += 1
            total = world.balance.level_up.freeze_steps
            if slowdown_steps(self._freeze_steps, total) > total - world.freezing:
                advance()
                return True
            return False
        self._freeze_steps = 0
        advance()
        return True

    def handle_event(self, world: World, event: pygame.event.Event) -> None:
        """Las teclas, los botones y el stick, si la mano está abierta."""
        if not world.hand or self.demo:
            return
        command = hand_command(event) or self.stick.command(event)
        if command is not None:
            self._lay_out(world)
            self.command(world, command)

    def command(self, world: World, command: HandCommand) -> None:
        """Hace lo que pide `command` con la mano de `world`."""
        count = len(world.hand)
        match command:
            case "left" | "right":
                delta = -1 if command == "left" else 1
                self.selected = (self.selected + delta) % count
            case "flip_up" | "flip_down":
                card = self._cards[self.selected]
                # Si estaba a medio girar, vuelve desde donde iba.
                flip = 1 - card.flip if card.flip < 1 else 0.0
                direction = -1 if command == "flip_up" else 1
                self._cards[self.selected] = CardPose(1 - card.face, flip, direction)
            case "choose":
                world.choose(self.selected)
                self._leaving = FALL_STEPS
            case "reroll":
                world.reroll()
            case "banish":
                world.banish(self.selected)

    def draw(
        self,
        screen: pygame.Surface,
        viewport: Viewport,
        world: World,
        palette: Palette,
    ) -> None:
        """La sombra, `dt = 0` y las tarjetas, si hay mano, frenado o tarjetas que
        bajan."""
        if world.hand:
            self._lay_out(world)
            # La sombra ya llegó a 1 en el frenado: no vuelve a empezar con las tarjetas.
            rise, shade = min(1.0, self._open_steps / RISE_STEPS), 1.0
        elif self._leaving > 0:
            rise = shade = self._leaving / FALL_STEPS
        elif world.freezing > 0:
            # Sin tarjetas todavía: el juego se oscurece mientras frena.
            shade = self._freeze_steps / (2 * world.balance.level_up.freeze_steps)
            pose = HandPose((), 0, 0.0, shade, 0.0, "")
            draw_hand(screen, viewport, [], pose, palette)
            return
        else:
            return
        hint = "" if self.demo else self._hint(world)
        cards = tuple(self._cards)
        pose = HandPose(cards, self.selected, rise, shade, self._time, hint)
        draw_hand(screen, viewport, self._views, pose, palette)

    def _lay_out(self, world: World) -> None:
        """Si el mundo trae una mano que no está dibujada, la arma: la primera, la
        siguiente de un nivel doble o la de un reroll. Si solo le falta la tarjeta que
        sacó un banish, deja lo demás como estaba."""
        if world.hand is self._shown:
            return
        banished = bool(world.hand) and set(world.hand) < set(self._shown)
        if banished:
            kept = [i for i, offer in enumerate(self._shown) if offer in world.hand]
            self._cards = [self._cards[i] for i in kept]
            self.selected = min(self.selected, len(world.hand) - 1)
        else:
            self._cards = [CardPose(0, 1.0, 1) for _ in world.hand]
            self.selected = 0
            self._open_steps = 0
            self._time = 0.0
        self._shown = world.hand
        self._views = card_views(world)

    def _play_demo(self, world: World) -> None:
        """La demo da sus órdenes a su hora, y si ninguna eligió, elige al azar con su
        `Random`, como la simulación, medio segundo después de la última."""
        for seconds, command in self.moves:
            if self._open_steps == round(seconds / STEP):
                self.command(world, command)
                return
        last = max((seconds for seconds, _ in self.moves), default=0.0)
        if self._open_steps >= max(DEMO_CHOOSE_STEPS, round((last + 0.5) / STEP)):
            self.selected = pick_at_random(world, self.chooser)
            self.command(world, "choose")

    @staticmethod
    def _hint(world: World) -> str:
        return (
            "← → mover · ↑ ↓ dar vuelta · Enter elegir"
            f" · R otra mano ({world.rerolls}) · B sacar ({world.banishes})"
        )
