"""Test de humo: el paquete se importa y `world` puede usar `Vector2` sin abrir pantalla."""

import pygame
from pygame.math import Vector2

import circlebh.world


def test_world_se_importa_sin_inicializar_pygame() -> None:
    assert circlebh.world.__doc__ is not None
    assert not pygame.get_init()


def test_vector2_funciona_sin_pygame_init() -> None:
    assert Vector2(3, 4).length() == 5
    assert not pygame.get_init()
