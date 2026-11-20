"""El plano cartesiano vacío: las franjas, el fondo y los dos ejes."""

import pygame
from pygame.math import Vector2

from circlebh.render.palette import Palette
from circlebh.viewport import Viewport

AXIS_WIDTH = 1.0
"""Grosor de los ejes, en unidades del plano: escala con la cámara."""


def draw_letterbox(
    screen: pygame.Surface, viewport: Viewport, palette: Palette
) -> None:
    """Pinta las franjas y, encima, el fondo del área útil."""
    screen.fill(palette.letterbox)
    screen.fill(palette.background, viewport.rect)


def draw_axes(screen: pygame.Surface, viewport: Viewport, palette: Palette) -> None:
    """Dibuja los ejes X e Y, fijos en el plano, de borde a borde del área útil.

    Quien llama recorta al área útil con `set_clip`: así un eje grueso pegado al borde
    no pinta la franja. Si el origen queda lejos de la vista, no se dibuja nada.
    """
    left, top, width, height = viewport.rect
    origin_x, origin_y = viewport.to_screen(Vector2(0, 0))
    line_width = viewport.width(AXIS_WIDTH)
    # El margen del grosor deja dibujar el eje cuando su centro cae justo fuera del área
    # pero su borde todavía se ve.
    if top - line_width <= origin_y <= top + height + line_width:
        pygame.draw.line(
            screen,
            palette.foreground,
            (left, origin_y),
            (left + width, origin_y),
            line_width,
        )
    if left - line_width <= origin_x <= left + width + line_width:
        pygame.draw.line(
            screen,
            palette.foreground,
            (origin_x, top),
            (origin_x, top + height),
            line_width,
        )
