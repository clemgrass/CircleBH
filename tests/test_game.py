"""Tests de la partida: `World` avanza un paso por `update`."""

import random
from dataclasses import replace

import pytest
from pygame.math import Vector2

from circlebh.balance import BALANCE
from circlebh.world.clock import STEP
from circlebh.world.game import World
from circlebh.world.polygon import polygon_edge
from circlebh.world.weapons import PointWeapon


def test_world_mueve_al_jugador() -> None:
    world = World(BALANCE, random.Random(1))
    world.update(Vector2(0, 1))
    assert world.player.position.y == pytest.approx(BALANCE.player.speed * STEP)


def test_world_empieza_con_un_hexagono_a_la_distancia_de_aparicion() -> None:
    world = World(BALANCE, random.Random(1))
    [enemy] = world.enemies
    assert len(enemy.edges) == BALANCE.enemies["hexagon"].sides
    assert enemy.position.length() == pytest.approx(BALANCE.spawning.distance)


def test_mundo_parte_con_el_arma_punto() -> None:
    world = World(BALANCE, random.Random(1))
    [weapon] = world.weapons
    assert isinstance(weapon, PointWeapon)
    assert weapon.spec == BALANCE.point_weapon


def test_la_bala_nace_donde_quedo_el_jugador() -> None:
    world = World(BALANCE, random.Random(1))
    world.update(Vector2(1, 0))
    [weapon] = world.weapons
    assert isinstance(weapon, PointWeapon)
    [bullet] = weapon.bullets
    assert bullet.position == world.player.position


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


def test_world_empieza_sin_terminar_y_en_cero() -> None:
    world = World(BALANCE, random.Random(1))
    assert world.game_over is False
    assert world.elapsed == 0


def test_elapsed_cuenta_un_step_por_update() -> None:
    world = World(BALANCE, random.Random(1))
    for _ in range(90):
        world.update(Vector2())
    assert world.steps == 90
    assert world.elapsed == pytest.approx(1.5)


# --- Morir ---


def mundo_con_hexagono_quieto(x: float) -> World:
    """Un mundo con el hexágono quieto (`speed = 0`) en `(x, 0)`, a la derecha del jugador.

    Quieto, la geometría queda exacta y no depende del redondeo de su paso. La línea
    que mira al jugador es la arista 1, la vertical izquierda del hexágono.
    """
    hexagon = replace(BALANCE.enemies["hexagon"], speed=0.0)
    world = World(replace(BALANCE, enemies={"hexagon": hexagon}), random.Random(1))
    [enemy] = world.enemies
    enemy.position = Vector2(x, 0)
    enemy.previous = Vector2(enemy.position)
    return world


def tangente() -> float:
    """El centro del hexágono al que su arista 1 queda tangente al jugador."""
    a, _ = polygon_edge(BALANCE.enemies["hexagon"].radius, 6, 1)
    return BALANCE.player.radius - a.x


def test_tocar_una_linea_termina_la_partida() -> None:
    world = mundo_con_hexagono_quieto(tangente() - 5)
    world.update(Vector2())
    assert world.game_over is True


def test_tangente_a_una_linea_termina_la_partida() -> None:
    world = mundo_con_hexagono_quieto(tangente())
    world.update(Vector2())
    assert world.game_over is True


def test_a_una_unidad_de_la_linea_no_muere() -> None:
    world = mundo_con_hexagono_quieto(tangente() + 1)
    world.update(Vector2())
    assert world.game_over is False


def test_dentro_de_un_enemigo_abierto_sin_tocar_no_muere() -> None:
    # Decisión 16: el jugador (radio 12) cabe dentro del hexágono (apotema ≈ 20,8) sin
    # tocar sus líneas. Solo llega ahí por un hueco.
    world = mundo_con_hexagono_quieto(0)
    world.enemies[0].remove_edge(1)
    world.update(Vector2())
    assert world.game_over is False


def test_la_envolvente_sola_no_mata() -> None:
    # Negativo: el jugador toca el círculo envolvente (a 24 + 12 = 36 del centro), pero
    # ninguna línea.
    world = mundo_con_hexagono_quieto(34)
    world.update(Vector2())
    assert world.game_over is False


def test_enemigo_lejos_no_termina_la_partida() -> None:
    world = World(BALANCE, random.Random(1))
    for _ in range(60):
        world.update(Vector2())
    assert world.game_over is False


def test_tras_morir_update_no_avanza() -> None:
    world = World(BALANCE, random.Random(1))
    world.enemies[0].position = Vector2(tangente() - 5, 0)
    world.update(Vector2())
    assert world.game_over is True

    jugador, enemigo, tiempo = (
        Vector2(world.player.position),
        Vector2(world.enemies[0].position),
        world.elapsed,
    )
    for _ in range(10):
        world.update(Vector2(1, 0))
    assert world.player.position == jugador
    assert world.enemies[0].position == enemigo
    assert world.elapsed == tiempo
    assert world.game_over is True


def test_world_sin_intencion_deja_al_jugador_quieto() -> None:
    world = World(BALANCE, random.Random(1))
    for _ in range(10):
        world.update(Vector2(0, 0))
    assert world.player.position == Vector2(0, 0)
