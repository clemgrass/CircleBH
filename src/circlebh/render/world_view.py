"""Dibuja lo que hay en `world` sobre el plano."""

from collections.abc import Callable

import pygame
from pygame.math import Vector2

from circlebh.world.game import World

PLAYER_COLOR = pygame.Color("white")

type ToScreen = Callable[[Vector2], tuple[float, float]]
"""Pasa un punto del plano (Y hacia arriba) a píxeles de la pantalla (Y hacia abajo)."""


def draw_world(screen: pygame.Surface, world: World, to_screen: ToScreen) -> None:
    """Dibuja al jugador como un círculo relleno."""
    player = world.player
    pygame.draw.circle(screen, PLAYER_COLOR, to_screen(player.position), player.radius)
