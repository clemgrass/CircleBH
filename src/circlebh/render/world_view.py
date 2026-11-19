"""Dibuja lo que hay en `world` sobre el plano, a través de la cámara."""

import pygame

from circlebh.viewport import Viewport
from circlebh.world.game import World

PLAYER_COLOR = pygame.Color("white")


def draw_world(screen: pygame.Surface, world: World, viewport: Viewport) -> None:
    """Dibuja al jugador como un círculo relleno, con su radio escalado por la cámara."""
    player = world.player
    pygame.draw.circle(
        screen,
        PLAYER_COLOR,
        viewport.to_screen(player.position),
        player.radius * viewport.scale,
    )
