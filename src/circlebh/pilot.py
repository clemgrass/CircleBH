"""El piloto de la demo: mueve al jugador sin teclado, para `--demo` y las capturas."""

import math

from pygame.math import Vector2

from circlebh.world.clock import STEP

LAP_SECONDS = 4.0
"""Cuánto tarda el piloto en dar una vuelta completa."""


def pilot_intent(step: int) -> Vector2:
    """La intención en el paso `step`: un círculo antihorario que parte hacia +x.

    La dirección gira a velocidad constante, así que el jugador recorre un círculo.
    """
    angle = math.tau * step * STEP / LAP_SECONDS
    return Vector2(math.cos(angle), math.sin(angle))
