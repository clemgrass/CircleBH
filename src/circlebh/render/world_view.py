"""Dibuja lo que hay en `world` sobre el plano, a través de la cámara."""

import pygame
from pygame.math import Vector2

from circlebh.render.palette import Palette
from circlebh.viewport import Viewport
from circlebh.world.figures import local_lines
from circlebh.world.game import World
from circlebh.world.weapons import PointWeapon

BULLET_DRAW_RADIUS = 3.0
"""Radio con que se dibuja la bala, en unidades del plano. Solo es visual: para chocar,
la bala es un punto."""
ENEMY_LINE_WIDTH = 2.0
"""Grosor de las líneas del enemigo, en unidades del plano: escala con la cámara."""
HITBOX_COLOR = pygame.Color("magenta")
HITBOX_WIDTH = 1.0
"""Grosor del círculo de choque, en unidades del plano: escala con la cámara."""


def draw_world(
    screen: pygame.Surface,
    world: World,
    viewport: Viewport,
    palette: Palette,
    show_hitboxes: bool,
) -> None:
    """Dibuja al jugador como un círculo relleno, a cada enemigo con las líneas que le
    quedan, sin relleno, las balas del jugador debajo, como puntos, y las balas enemigas
    encima, con el acento. La gran estrella roja va con el acento: su aviso titila
    encima del jugador, y al irse se apaga hacia el fondo.

    Con `show_hitboxes`, encima va el círculo de cada cuerpo.
    """
    for weapon in world.weapons:
        if isinstance(weapon, PointWeapon):
            for bullet in weapon.bullets:
                pygame.draw.circle(
                    screen,
                    palette.foreground,
                    viewport.to_screen(bullet.position),
                    BULLET_DRAW_RADIUS * viewport.scale,
                )

    player = world.player
    pygame.draw.circle(
        screen,
        palette.foreground,
        viewport.to_screen(player.position),
        player.radius * viewport.scale,
    )
    line_width = viewport.width(ENEMY_LINE_WIDTH)
    for enemy in world.enemies:
        # Lo rojo no choca con los enemigos: los fantasmas van con el acento.
        color = palette.accent if enemy.spec.phantom else palette.foreground
        draw_lines(screen, viewport, enemy.lines(), color, line_width)

    merge = world.merge
    if merge.blink(world.steps):
        # El aviso: la silueta de la gran estrella, encima del jugador.
        shape, radius = merge.into.shape, merge.into.radius
        silhouette = [
            (player.position + a, player.position + b)
            for a, b in local_lines(shape, radius)
        ]
        draw_lines(screen, viewport, silhouette, palette.accent, line_width)
    if merge.fading is not None:
        # Se apaga: el acento se mezcla con el fondo hasta desaparecer.
        color = palette.background.lerp(palette.accent, merge.fade(world.steps))
        draw_lines(screen, viewport, merge.fading.lines(), color, line_width)

    # Las balas enemigas van encima de todo, con el acento: lo que mata se ve siempre.
    radius = world.balance.enemy_bullet.radius * viewport.scale
    for enemy_bullet in world.enemy_bullets:
        pygame.draw.circle(
            screen,
            palette.accent,
            viewport.to_screen(enemy_bullet.position),
            radius,
        )

    if show_hitboxes:
        # El jugador choca como círculo. Del enemigo se dibuja la envolvente, el primer
        # descarte: lo que choca son sus líneas (ADR 0020).
        bodies = [(player.position, player.radius)]
        bodies += [(enemy.position, enemy.radius) for enemy in world.enemies]
        for position, radius in bodies:
            draw_hitbox(screen, viewport, position, radius)


def draw_lines(
    screen: pygame.Surface,
    viewport: Viewport,
    lines: list[tuple[Vector2, Vector2]],
    color: pygame.Color,
    width: int,
) -> None:
    """Las líneas `lines` del plano, con `color`."""
    for a, b in lines:
        pygame.draw.line(
            screen, color, viewport.to_screen(a), viewport.to_screen(b), width
        )


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
