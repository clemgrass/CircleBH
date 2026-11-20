"""Tests de la partida: `World` avanza un paso por `update`."""

import random

import pytest
from pygame.math import Vector2

from circlebh.balance import BALANCE
from circlebh.world.clock import STEP
from circlebh.world.game import World
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


def separacion_de_contacto(world: World) -> float:
    """La distancia entre centros a la que el jugador y el enemigo quedan tangentes."""
    return world.player.radius + world.enemies[0].radius


def test_contacto_termina_la_partida() -> None:
    world = World(BALANCE, random.Random(1))
    world.enemies[0].position = Vector2(separacion_de_contacto(world) / 2, 0)
    world.update(Vector2())
    assert world.game_over is True


def test_contacto_tangente_termina_la_partida() -> None:
    # Tras el paso, el enemigo queda justo tangente al jugador: eso ya es tocarlo.
    world = World(BALANCE, random.Random(1))
    paso = BALANCE.enemies["hexagon"].speed * STEP
    world.enemies[0].position = Vector2(separacion_de_contacto(world) + paso, 0)
    world.update(Vector2())
    assert world.game_over is True


def test_enemigo_a_una_unidad_no_termina_la_partida() -> None:
    world = World(BALANCE, random.Random(1))
    paso = BALANCE.enemies["hexagon"].speed * STEP
    world.enemies[0].position = Vector2(0, separacion_de_contacto(world) + paso + 1)
    world.update(Vector2())
    assert world.game_over is False


def test_enemigo_lejos_no_termina_la_partida() -> None:
    world = World(BALANCE, random.Random(1))
    for _ in range(60):
        world.update(Vector2())
    assert world.game_over is False


def test_tras_morir_update_no_avanza() -> None:
    world = World(BALANCE, random.Random(1))
    world.enemies[0].position = Vector2(0, 0)
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
