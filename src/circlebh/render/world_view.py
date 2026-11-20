"""Dibuja lo que hay en `world` sobre el plano, a través de la cámara."""

import pygame
from pygame.math import Vector2

from circlebh.viewport import Viewport
from circlebh.world.enemy import regular_polygon
from circlebh.world.game import World
from circlebh.world.weapons import PointWeapon

PLAYER_COLOR = pygame.Color("white")
WEAPON_COLOR = pygame.Color("white")
BULLET_DRAW_RADIUS = 3.0
"""Radio con que se dibuja la bala, en unidades del plano. Solo es visual: para chocar,
la bala es un punto."""
# Provisorio: el color de acento sigue abierto hasta que existan balas enemigas.
ENEMY_COLOR = pygame.Color("white")
HITBOX_COLOR = pygame.Color("magenta")
HITBOX_WIDTH = 1.0
"""Grosor del círculo de choque, en unidades del plano: escala con la cámara."""


def draw_world(
    screen: pygame.Surface, world: World, viewport: Viewport, show_hitboxes: bool
) -> None:
    """Dibuja al jugador como un círculo y a cada enemigo como un polígono, rellenos, y
    las balas del jugador debajo, como puntos.

    Con `show_hitboxes`, encima va el círculo de choque de cada cuerpo.
    """
    for weapon in world.weapons:
        if isinstance(weapon, PointWeapon):
            for bullet in weapon.bullets:
                pygame.draw.circle(
                    screen,
                    WEAPON_COLOR,
                    viewport.to_screen(bullet.position),
                    BULLET_DRAW_RADIUS * viewport.scale,
                )

    player = world.player
    pygame.draw.circle(
        screen,
        PLAYER_COLOR,
        viewport.to_screen(player.position),
        player.radius * viewport.scale,
    )
    for enemy in world.enemies:
        vertices = regular_polygon(enemy.position, enemy.radius, enemy.sides)
        pygame.draw.polygon(
            screen, ENEMY_COLOR, [viewport.to_screen(v) for v in vertices]
        )

    if show_hitboxes:
        bodies = [(player.position, player.radius)]
        bodies += [(enemy.position, enemy.radius) for enemy in world.enemies]
        for position, radius in bodies:
            draw_hitbox(screen, viewport, position, radius)


def draw_hitbox(
    screen: pygame.Surface, viewport: Viewport, position: Vector2, radius: float
) -> None:
    """El círculo de choque, solo el borde."""
    pygame.draw.circle(
        screen,
        HITBOX_COLOR,
        viewport.to_screen(position),
        radius * viewport.scale,
        viewport.width(HITBOX_WIDTH),
    )
