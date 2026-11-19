"""La partida en pantalla: lee la entrada, avanza `world` paso a paso y lo dibuja."""

import pygame
import pygame._sdl2.controller as sdl_controller
from pygame.math import Vector2

from circlebh.controls import axis_to_unit, combine, keyboard_intent, stick_intent
from circlebh.pilot import pilot_intent
from circlebh.render.plane import draw_empty_plane
from circlebh.render.world_view import ToScreen, draw_world
from circlebh.scenes.scenarios import Scenario
from circlebh.settings import Settings
from circlebh.world.game import World


class Gamepads:
    """Los controles conectados. Se pueden conectar y desconectar con el juego abierto.

    Usa la API de controles de SDL, con el layout con nombre (ADR 0019). Es el único
    módulo del juego que la toca; fuera del juego, solo `tools/diagnostico_control.py`.
    Cada control se guarda con el `instance_id` de su
    joystick: el alta trae `device_index` y la baja trae `instance_id`.
    """

    def __init__(self) -> None:
        sdl_controller.init()
        self._pads: dict[int, sdl_controller.Controller] = {}

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.CONTROLLERDEVICEADDED:
            try:
                pad = sdl_controller.Controller(event.device_index)
            except pygame.error:
                # Se desconectó entre el aviso y la apertura: llega su baja y listo.
                return
            self._pads[pad.as_joystick().get_instance_id()] = pad
        elif (
            event.type == pygame.CONTROLLERDEVICEREMOVED
            and event.instance_id in self._pads
        ):
            # Hay que soltarlo: un control quitado sigue devolviendo su último valor,
            # y un stick inclinado al desconectar movería al jugador para siempre.
            self._pads.pop(event.instance_id).quit()

    def intents(self, deadzone: float) -> list[Vector2]:
        """La intención de cada control conectado: el stick izquierdo y la cruceta."""
        intents = []
        for pad in self._pads.values():
            if not pad.attached():
                continue
            x = axis_to_unit(pad.get_axis(pygame.CONTROLLER_AXIS_LEFTX))
            y = axis_to_unit(pad.get_axis(pygame.CONTROLLER_AXIS_LEFTY))
            intents.append(stick_intent(x, y, deadzone))
            intents.append(
                keyboard_intent(
                    left=pad.get_button(pygame.CONTROLLER_BUTTON_DPAD_LEFT),
                    right=pad.get_button(pygame.CONTROLLER_BUTTON_DPAD_RIGHT),
                    up=pad.get_button(pygame.CONTROLLER_BUTTON_DPAD_UP),
                    down=pad.get_button(pygame.CONTROLLER_BUTTON_DPAD_DOWN),
                )
            )
        return intents


def keys_intent() -> Vector2:
    """WASD y flechas."""
    keys = pygame.key.get_pressed()
    return keyboard_intent(
        left=keys[pygame.K_a] or keys[pygame.K_LEFT],
        right=keys[pygame.K_d] or keys[pygame.K_RIGHT],
        up=keys[pygame.K_w] or keys[pygame.K_UP],
        down=keys[pygame.K_s] or keys[pygame.K_DOWN],
    )


def centered(screen: pygame.Surface) -> ToScreen:
    """El origen del plano en el centro de la ventana, 1 unidad = 1 píxel, Y invertida.

    Provisorio: la cámara de la tarea 2 (`viewport.py`) lo reemplaza.
    """
    width, height = screen.get_size()
    return lambda p: (width / 2 + p.x, height / 2 - p.y)


class GameScene:
    """Una partida. Con `demo`, el escenario manda y no se lee la entrada."""

    def __init__(
        self, world: World, settings: Settings, demo: Scenario | None = None
    ) -> None:
        self.world = world
        self.settings = settings
        self.demo = demo
        self.gamepads = Gamepads() if demo is None else None
        self.steps = 0

    def handle_event(self, event: pygame.event.Event) -> None:
        if self.gamepads is not None:
            self.gamepads.handle_event(event)

    def step(self) -> None:
        """Avanza `world` un paso con la intención de este momento."""
        self.world.update(self.intent())
        self.steps += 1

    def intent(self) -> Vector2:
        if self.demo is not None:
            return pilot_intent(self.steps) if self.demo.pilot else Vector2()
        assert self.gamepads is not None
        deadzone = self.settings.controls.stick_deadzone
        return combine(keys_intent(), *self.gamepads.intents(deadzone))

    def draw(self, screen: pygame.Surface) -> None:
        draw_empty_plane(screen)
        draw_world(screen, self.world, centered(screen))
