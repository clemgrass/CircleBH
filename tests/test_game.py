"""Tests de la partida: `World` avanza un paso por `update`."""

import random

import pytest
from pygame.math import Vector2

from circlebh.balance import BALANCE
from circlebh.world.clock import STEP
from circlebh.world.game import World


def test_world_mueve_al_jugador() -> None:
    world = World(BALANCE, random.Random(1))
    world.update(Vector2(0, 1))
    assert world.player.position.y == pytest.approx(BALANCE.player.speed * STEP)


def test_world_sin_intencion_deja_al_jugador_quieto() -> None:
    world = World(BALANCE, random.Random(1))
    for _ in range(10):
        world.update(Vector2(0, 0))
    assert world.player.position == Vector2(0, 0)
