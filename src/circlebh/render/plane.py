"""El plano cartesiano vacío: las franjas, el fondo y los dos ejes."""

import pygame
from pygame.math import Vector2

from circlebh.viewport import Viewport

# Provisorio: el fondo negro o blanco se decide con un prototipo (pregunta abierta).
BACKGROUND = pygame.Color("black")
# Provisorio, como el fondo: se revisa en la Tarea 8.
LETTERBOX = pygame.Color("#202020")
AXIS_COLOR = pygame.Color("white")
AXIS_WIDTH = 1.0
"""Grosor de los ejes, en unidades del plano: escala con la cámara."""


def draw_plane(screen: pygame.Surface, viewport: Viewport) -> None:
    """Pinta las franjas y el fondo, y dibuja los ejes X e Y, fijos en el plano.

    Los ejes cruzan el área útil de borde a borde. Si el origen queda fuera de la vista,
    no se ven.
    """
    screen.fill(LETTERBOX)
    screen.fill(BACKGROUND, viewport.rect)
    left, top, width, height = viewport.rect
    origin_x, origin_y = viewport.to_screen(Vector2(0, 0))
    line_width = viewport.width(AXIS_WIDTH)
    if top <= origin_y <= top + height:
        pygame.draw.line(
            screen,
            AXIS_COLOR,
            (left, origin_y),
            (left + width - 1, origin_y),
            line_width,
        )
    if left <= origin_x <= left + width:
        pygame.draw.line(
            screen,
            AXIS_COLOR,
            (origin_x, top),
            (origin_x, top + height - 1),
            line_width,
        )
