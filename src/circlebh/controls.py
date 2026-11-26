"""La intención de movimiento: teclas y ejes del control convertidos en un `Vector2`.

La intención mide de 0 a 1 y usa las coordenadas de `world`, con Y hacia arriba.
`world` no sabe de dónde viene: aquí se juntan el teclado, el stick y la cruceta.
Leer los dispositivos es trabajo de `scenes/`; este módulo solo hace las cuentas.
"""

from typing import Literal

import pygame
from pygame.math import Vector2

AXIS_MAX = 32767
"""El valor máximo de un eje del control en SDL. El mínimo es −32768."""


def keyboard_intent(*, left: bool, right: bool, up: bool, down: bool) -> Vector2:
    """Cuatro direcciones apretadas o no, en una intención de largo 0 o 1.

    La diagonal se normaliza: si no, avanzaría √2 veces más rápido.
    Sirve igual para la cruceta del control.
    """
    intent = Vector2(int(right) - int(left), int(up) - int(down))
    if intent.length_squared() > 0:
        intent.normalize_ip()
    return intent


def axis_to_unit(raw: int) -> float:
    """Un eje del control, de −32768 a 32767, en −1..1."""
    return max(raw / AXIS_MAX, -1.0)


def stick_intent(x: float, y: float, deadzone: float) -> Vector2:
    """La posición del stick, con cada eje en −1..1, en una intención de largo 0 a 1.

    - La Y se invierte: el stick da Y positiva hacia abajo, y `world` la usa hacia arriba.
    - Dentro de la zona muerta (un círculo de radio `deadzone`), da cero.
    - Fuera, reescala el largo para que el borde de la zona muerta valga 0 y el tope, 1.
    - La dirección no cambia.
    """
    intent = Vector2(x, -y)
    length = intent.length()
    if length <= deadzone:
        return Vector2()
    scaled = min((length - deadzone) / (1 - deadzone), 1.0)
    return intent * (scaled / length)


RESTART_BUTTONS = (pygame.CONTROLLER_BUTTON_A, pygame.CONTROLLER_BUTTON_X)
"""Los botones que reinician, con el layout con nombre de SDL (ADR 0019).

A es el de abajo y X, el de la izquierda. Así "X" sirve en los dos controles comunes:
en PlayStation es la ✕ (A en SDL), y en Xbox, la X. De paso, el □ y la A también.
"""


def is_restart(event: pygame.event.Event) -> bool:
    """Si el evento pide reiniciar: apretar R, o un botón de `RESTART_BUTTONS`."""
    return (event.type == pygame.KEYDOWN and event.key == pygame.K_r) or (
        event.type == pygame.CONTROLLERBUTTONDOWN and event.button in RESTART_BUTTONS
    )


type HandCommand = Literal[
    "left", "right", "flip_up", "flip_down", "choose", "reroll", "banish"
]


"""Lo que se puede hacer con la mano abierta: moverse entre tarjetas, darlas vuelta
hacia arriba o hacia abajo, elegir, cambiar la mano entera o sacar una tarjeta."""

HAND_KEYS: dict[int, HandCommand] = {
    pygame.K_LEFT: "left",
    pygame.K_a: "left",
    pygame.K_RIGHT: "right",
    pygame.K_d: "right",
    pygame.K_UP: "flip_up",
    pygame.K_w: "flip_up",
    pygame.K_DOWN: "flip_down",
    pygame.K_s: "flip_down",
    pygame.K_RETURN: "choose",
    pygame.K_KP_ENTER: "choose",
    pygame.K_r: "reroll",
    pygame.K_b: "banish",
}
"""Las teclas de la mano (decisión 8). R y B no chocan con nada: R reinicia solo
después de morir, y con la mano abierta no se puede estar muerto."""

HAND_BUTTONS: dict[int, HandCommand] = {
    pygame.CONTROLLER_BUTTON_DPAD_LEFT: "left",
    pygame.CONTROLLER_BUTTON_DPAD_RIGHT: "right",
    pygame.CONTROLLER_BUTTON_DPAD_UP: "flip_up",
    pygame.CONTROLLER_BUTTON_DPAD_DOWN: "flip_down",
    pygame.CONTROLLER_BUTTON_A: "choose",
    pygame.CONTROLLER_BUTTON_Y: "reroll",
    pygame.CONTROLLER_BUTTON_X: "banish",
}
"""Los botones de la mano, con el layout con nombre de SDL (ADR 0019): se elige con el
de abajo, se cambia la mano con el de arriba y se saca una tarjeta con el de la
izquierda."""


def hand_command(event: pygame.event.Event) -> HandCommand | None:
    """La orden de la mano que da una tecla o un botón apretado, o `None`."""
    if event.type == pygame.KEYDOWN:
        return HAND_KEYS.get(event.key)
    if event.type == pygame.CONTROLLERBUTTONDOWN:
        return HAND_BUTTONS.get(event.button)
    return None


STICK_STEP = 0.5
"""Cuánto hay que inclinar el stick, de 0 a 1, para que cuente como una flecha."""


class StickSteps:
    """El stick izquierdo como flechas: una orden cada vez que un eje cruza
    `STICK_STEP` hacia afuera. Mantenerlo inclinado no repite; hay que volver."""

    def __init__(self) -> None:
        self._sides: dict[int, int] = {}
        """Hacia qué lado está cada eje: −1, 0 o 1."""

    def command(self, event: pygame.event.Event) -> HandCommand | None:
        """La orden que da `event`, si es un eje del stick izquierdo que cruzó."""
        if event.type != pygame.CONTROLLERAXISMOTION:
            return None
        if event.axis == pygame.CONTROLLER_AXIS_LEFTX:
            commands: tuple[HandCommand, HandCommand] = ("left", "right")
        elif event.axis == pygame.CONTROLLER_AXIS_LEFTY:
            # SDL da la Y positiva hacia abajo.
            commands = ("flip_up", "flip_down")
        else:
            return None
        value = axis_to_unit(event.value)
        side = (value >= STICK_STEP) - (value <= -STICK_STEP)
        before = self._sides.get(event.axis, 0)
        self._sides[event.axis] = side
        if side == 0 or side == before:
            return None
        return commands[0] if side < 0 else commands[1]


def combine(*intents: Vector2) -> Vector2:
    """Suma las intenciones de todas las fuentes y recorta el resultado a largo 1."""
    total = sum(intents, Vector2())
    return total.clamp_magnitude(1)
