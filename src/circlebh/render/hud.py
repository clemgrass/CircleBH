"""Lo que se dibuja sobre la pantalla y no sobre el plano: el borde de la experiencia
(spec de la 0.3.0, decisión 12).

Una línea fina, cerca del borde del área útil, se carga desde la esquina de arriba a la
izquierda en el sentido del reloj. Una vuelta completa es un nivel. No hay número.
"""

import itertools
import math

import pygame

from circlebh.render.palette import Palette
from circlebh.viewport import Viewport

BORDER_INSET = 6
"""A cuántos píxeles del borde del área útil va la línea."""
BORDER_WIDTH = 2
"""El grosor de la línea, en píxeles."""
BORDER_GLOW = ((9, 40), (5, 90))
"""El halo de la línea: pasadas más anchas y transparentes debajo de ella, como
`(grosor en píxeles, opacidad de 0 a 255)`."""
BORDER_EASE = 0.25
"""La constante de tiempo de la transición, en segundos: en ese tiempo, el borde
recorre el 63 % de lo que le falta para alcanzar la experiencia del mundo."""


def ease_toward(shown: float, target: float, dt: float) -> float:
    """Acerca `shown` a `target` en `dt` segundos, sin pasarse: la transición suave.

    Es el decaimiento exponencial `shown + (target − shown)·(1 − e^{−dt/τ})`: avanza
    rápido cuando falta mucho y frena al llegar, sin depender de cuántos cuadros haya.
    """
    return shown + (target - shown) * (1 - math.exp(-dt / BORDER_EASE))


def border_path(
    rect: tuple[int, int, int, int], fraction: float
) -> list[tuple[float, float]]:
    """Los puntos del borde cargado hasta `fraction` ∈ [0, 1] de la vuelta, desde la
    esquina de arriba a la izquierda y en el sentido del reloj, ya en píxeles."""
    left, top, width, height = rect
    x0, y0 = left + BORDER_INSET, top + BORDER_INSET
    x1, y1 = left + width - 1 - BORDER_INSET, top + height - 1 - BORDER_INSET
    corners = [(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)]
    left_to_walk = fraction * 2 * ((x1 - x0) + (y1 - y0))
    path: list[tuple[float, float]] = [corners[0]]
    for (ax, ay), (bx, by) in itertools.pairwise(corners):
        side = math.hypot(bx - ax, by - ay)
        if left_to_walk >= side:
            path.append((bx, by))
            left_to_walk -= side
            continue
        u = left_to_walk / side
        path.append((ax + (bx - ax) * u, ay + (by - ay) * u))
        break
    return path


def draw_experience_border(
    screen: pygame.Surface, viewport: Viewport, fraction: float, palette: Palette
) -> None:
    """La línea del borde cargada hasta `fraction` de la vuelta, con el color intermedio
    de la luz y su halo. Con 0 no dibuja nada."""
    if fraction <= 0:
        return
    path = border_path(viewport.rect, min(1.0, fraction))
    color = palette.light.selection
    # El halo va con transparencia: sobre una capa aparte que después se pega encima.
    overlay = _overlay(screen.get_size())
    overlay.fill((0, 0, 0, 0))
    for width, alpha in BORDER_GLOW:
        pygame.draw.lines(
            overlay, (color.r, color.g, color.b, alpha), False, path, width
        )
    screen.blit(overlay, (0, 0))
    pygame.draw.lines(screen, color, False, path, BORDER_WIDTH)


_overlays: dict[tuple[int, int], pygame.Surface] = {}


def _overlay(size: tuple[int, int]) -> pygame.Surface:
    """Una capa transparente del tamaño de la pantalla, la misma en cada cuadro."""
    if size not in _overlays:
        _overlays.clear()
        _overlays[size] = pygame.Surface(size, pygame.SRCALPHA)
    return _overlays[size]
