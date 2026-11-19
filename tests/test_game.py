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


def test_world_empieza_con_un_hexagono_a_la_distancia_de_aparicion() -> None:
    world = World(BALANCE, random.Random(1))
    [enemy] = world.enemies
    assert enemy.sides == BALANCE.enemies["hexagon"].sides
    assert enemy.position.length() == pytest.approx(BALANCE.spawning.distance)


def test_misma_semilla_el_enemigo_aparece_en_el_mismo_lugar() -> None:
    a = World(BALANCE, random.Random(7))
    b = World(BALANCE, random.Random(7))
    assert a.enemies[0].position == b.enemies[0].position


def test_el_enemigo_persigue_la_posicion_nueva_del_jugador() -> None:
    world = World(BALANCE, random.Random(1))
    enemy = world.enemies[0]
    enemy.position = Vector2(100, 0)
    # El jugador se mueve hacia arriba; el enemigo apunta a donde quedó, no al origen.
    world.update(Vector2(0, 1))
    hacia_el_jugador = world.player.position - Vector2(100, 0)
    avance = enemy.position - Vector2(100, 0)
    # La misma dirección, no los mismos bits.
    assert tuple(avance.normalize()) == pytest.approx(
        tuple(hacia_el_jugador.normalize())
    )


def test_world_sin_intencion_deja_al_jugador_quieto() -> None:
    world = World(BALANCE, random.Random(1))
    for _ in range(10):
        world.update(Vector2(0, 0))
    assert world.player.position == Vector2(0, 0)
