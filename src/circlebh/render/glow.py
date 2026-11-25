"""La luz difusa: un halo que se apaga hacia afuera (ADR 0031).

Se dibuja con transparencia, así que sirve igual sobre el fondo negro y sobre el blanco.
"""

from functools import cache

import pygame

GLOW_PEAK = 210
"""La opacidad del halo en su centro, de 0 a 255."""


@cache
def glow_surface(rgb: tuple[int, int, int], radius: int) -> pygame.Surface:
    """Un círculo de `radius` px cuyo alfa cae como `(1 − r/R)²` desde el centro.

    Se dibujan círculos rellenos de afuera hacia adentro, cada uno más opaco: en una
    superficie con alfa, `pygame.draw` escribe el píxel sin mezclar, así que el de
    adentro reemplaza al de afuera. Se guarda por color y radio: los puntos valen pocos
    valores distintos, y armarla en cada cuadro costaría más que dibujarla."""
    size = 2 * radius + 1
    surface = pygame.Surface((size, size), pygame.SRCALPHA)
    for r in range(radius, 0, -1):
        alpha = round(GLOW_PEAK * (1 - r / (radius + 1)) ** 2)
        pygame.draw.circle(surface, (*rgb, alpha), (radius, radius), r)
    return surface


def draw_glow(
    screen: pygame.Surface,
    center: tuple[float, float],
    radius: float,
    color: pygame.Color,
) -> None:
    """El halo de `color` y `radius` px, centrado en `center`."""
    r = max(1, round(radius))
    surface = glow_surface((color.r, color.g, color.b), r)
    screen.blit(surface, (round(center[0]) - r, round(center[1]) - r))
