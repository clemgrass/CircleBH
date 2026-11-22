"""Tests de las balas enemigas: puntos con radio que van en línea recta, más rápido que el
jugador. Atraviesan a los enemigos, matan al jugador y se borran lejos (spec de la
0.2.0, "Las balas enemigas").
"""

import math
import random
from dataclasses import replace
from itertools import groupby

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from pygame.math import Vector2

from circlebh.balance import BALANCE, VolleySpec
from circlebh.pilot import pilot_intent
from circlebh.world.actions import Volley, VolleyState
from circlebh.world.clock import STEP
from circlebh.world.enemy import Enemy
from circlebh.world.enemy_bullets import EnemyBullet, bullet_hits_player, step_bullets
from circlebh.world.game import World
from circlebh.world.player import Player

BULLET = BALANCE.enemy_bullet
HEXAGON = BALANCE.enemies["hexagon"]
REACH = BALANCE.player.radius + BULLET.radius
"""A esta distancia del centro del jugador, la bala lo toca."""


def bala(start: Vector2, end: Vector2) -> EnemyBullet:
    """Una bala que va de `start` a `end` en su próximo paso."""
    return EnemyBullet(start, (end - start) / STEP)


def jugador(before: Vector2, after: Vector2) -> Player:
    """Un jugador que en su último paso fue de `before` a `after`."""
    player = Player(BALANCE.player)
    player.position = Vector2(after)
    player.previous = Vector2(before)
    return player


# --- El movimiento ---


def test_bala_avanza_en_linea_recta() -> None:
    bullet = EnemyBullet(Vector2(10, 20), Vector2(60, -120))
    bullet.step()
    assert bullet.previous == Vector2(10, 20)
    assert bullet.position == Vector2(10 + 60 * STEP, 20 - 120 * STEP)


def test_bala_no_sigue_al_vector_que_la_creo() -> None:
    # Copia sus vectores: si el que dispara se mueve, la bala no lo sigue.
    origin = Vector2(5, 5)
    bullet = EnemyBullet(origin, Vector2(1, 0))
    origin.x = 99
    assert bullet.position == Vector2(5, 5)


def test_bala_mas_rapida_que_el_jugador() -> None:
    # Coherencia (decisión 10): no se la deja atrás corriendo; hay que esquivarla.
    assert BULLET.speed > BALANCE.player.speed


# --- El golpe al jugador ---


def test_bala_que_cruza_al_jugador_lo_mata() -> None:
    # Entre dos pasos pasa de un lado al otro, sin quedar nunca encima.
    bullet = bala(Vector2(-REACH - 5, 0), Vector2(REACH + 5, 0))
    bullet.step()
    assert bullet_hits_player(bullet, jugador(Vector2(), Vector2()), BULLET.radius)


def test_bala_que_roza_al_jugador_lo_mata() -> None:
    # Borde: tangente cuenta como tocarlo, como en `segment_touches_circle`.
    bullet = bala(Vector2(-50, REACH), Vector2(50, REACH))
    bullet.step()
    assert bullet_hits_player(bullet, jugador(Vector2(), Vector2()), BULLET.radius)


def test_bala_que_pasa_al_lado_no_mata() -> None:
    bullet = bala(Vector2(-50, REACH + 0.5), Vector2(50, REACH + 0.5))
    bullet.step()
    assert not bullet_hits_player(bullet, jugador(Vector2(), Vector2()), BULLET.radius)


def test_bala_cuenta_el_paso_del_jugador() -> None:
    # Borde: la bala apenas se mueve, y el jugador le pasa por encima en un paso. En el
    # marco del jugador, la bala cruza su centro. Mirando solo dónde quedó, no la toca.
    bullet = bala(Vector2(0, -1), Vector2(0, 1))
    bullet.step()
    player = jugador(Vector2(-30, 0), Vector2(30, 0))
    assert bullet_hits_player(bullet, player, BULLET.radius)


def test_jugador_que_se_aparta_no_muere() -> None:
    # Negativo: la bala llega a donde estaba el jugador, pero él ya se fue.
    bullet = bala(Vector2(-50, 0), Vector2(0, 0))
    bullet.step()
    player = jugador(Vector2(), Vector2(0, REACH + 1))
    assert not bullet_hits_player(bullet, player, BULLET.radius)


# --- El borrado ---


def test_bala_lejana_se_borra() -> None:
    lejos = EnemyBullet(Vector2(100, 0), Vector2(60, 0))
    cerca = EnemyBullet(Vector2(10, 0), Vector2(60, 0))
    quedan = step_bullets([lejos, cerca], Vector2(), despawn=100)
    assert quedan == [cerca]


def test_bala_justo_en_despawn_sigue() -> None:
    # Borde: se borra al pasar `despawn`, no al llegar.
    # `60 · STEP` da 1 exacto en coma flotante: la bala queda en 100.
    bullet = EnemyBullet(Vector2(99, 0), Vector2(60, 0))
    assert step_bullets([bullet], Vector2(), despawn=100) == [bullet]
    assert bullet.position == Vector2(100, 0)


def test_step_bullets_avanza_cada_bala() -> None:
    bullet = EnemyBullet(Vector2(), Vector2(0, 60))
    step_bullets([bullet], Vector2(), despawn=100)
    assert tuple(bullet.position) == pytest.approx((0, 60 * STEP))


# --- En el mundo ---

SIN_APARICIONES = replace(
    BALANCE,
    director=replace(
        BALANCE.director,
        sections=(replace(BALANCE.director.sections[0], deck=()),),
    ),
)
"""El balance real con un director que no compra: los tests ponen a mano a los
enemigos."""

PENTAGON = BALANCE.enemies["pentagon"]
VOLLEY = PENTAGON.actions[0]
assert isinstance(VOLLEY, VolleySpec)
APUNTADO = replace(PENTAGON, spin=0.0)
"""Un pentágono que no gira: debajo del jugador, su primera punta le apunta siempre."""
DEBAJO = Vector2(0, -(VOLLEY.min_distance + VOLLEY.max_distance) / 2)


def mundo(*, lethal: bool = True) -> World:
    return World(SIN_APARICIONES, random.Random(1), lethal=lethal, armed=False)


def test_world_la_bala_mata_al_jugador_quieto() -> None:
    world = mundo()
    world.enemies = [Enemy(APUNTADO, DEBAJO)]
    for _ in range(round(3 / STEP)):
        world.update(Vector2())
    assert world.game_over
    assert world.enemy_bullets


def test_world_sin_lethal_la_bala_no_mata() -> None:
    world = mundo(lethal=False)
    world.enemies = [Enemy(APUNTADO, DEBAJO)]
    for _ in range(round(3 / STEP)):
        world.update(Vector2())
    assert not world.game_over


def test_bala_atraviesa_enemigos() -> None:
    # Negativo: un hexágono entre el pentágono y el jugador no pierde líneas, y se mueve
    # igual que si nadie disparara.
    dispara = mundo(lethal=False)
    callado = mundo(lethal=False)
    dispara.enemies = [Enemy(APUNTADO, DEBAJO), Enemy(HEXAGON, DEBAJO / 2)]
    callado.enemies = [
        Enemy(replace(APUNTADO, actions=()), DEBAJO),
        Enemy(HEXAGON, DEBAJO / 2),
    ]
    disparos = 0
    for _ in range(round(3 / STEP)):
        dispara.update(Vector2())
        callado.update(Vector2())
        disparos = max(disparos, len(dispara.enemy_bullets))
        a, b = dispara.enemies[1], callado.enemies[1]
        assert a.position == b.position
        assert a.velocity == b.velocity
        assert a.edges == list(range(HEXAGON.sides))
    assert disparos > 0


def test_world_borra_las_balas_lejanas() -> None:
    world = mundo()
    lejos = BALANCE.spawning.distance
    world.enemy_bullets = [
        EnemyBullet(Vector2(lejos, 0), Vector2(60, 0)),
        EnemyBullet(Vector2(-lejos + 10, 0), Vector2(60, 0)),
    ]
    world.update(Vector2())
    assert [b.position.x for b in world.enemy_bullets] == [-lejos + 11]


def test_la_bala_nace_y_se_mueve_en_el_paso_siguiente() -> None:
    # Como las balas del jugador: nace en el vértice y avanza desde el próximo paso.
    world = mundo()
    world.enemies = [Enemy(APUNTADO, DEBAJO)]
    while not world.enemy_bullets:
        world.update(Vector2())
    nacidas = [Vector2(b.position) for b in world.enemy_bullets]
    assert all(b.previous == b.position for b in world.enemy_bullets)
    world.update(Vector2())
    movidas = [b.position for b in world.enemy_bullets[: len(nacidas)]]
    for antes, ahora in zip(nacidas, movidas, strict=True):
        assert antes.distance_to(ahora) == pytest.approx(BULLET.speed * STEP)


# --- La propiedad (Hypothesis) ---

lugares = st.builds(
    lambda r, a: Vector2(r * math.cos(a), r * math.sin(a)),
    st.floats(min_value=60, max_value=500),
    st.floats(min_value=0, max_value=math.tau),
)


@settings(max_examples=15, deadline=None)
@given(pentagonos=st.lists(lugares, min_size=1, max_size=3))
def test_nunca_dispara_sin_avisar(pentagonos: list[Vector2]) -> None:
    # Con el piloto moviéndose, cada ráfaga va justo después de un aviso completo, y
    # cada bala nace en un paso en que su pentágono está disparando.
    world = World(SIN_APARICIONES, random.Random(1), lethal=False, armed=False)
    world.enemies = [Enemy(PENTAGON, p) for p in pentagonos]
    historia: dict[int, list[VolleyState]] = {id(e): [] for e in world.enemies}
    for _ in range(round(8 / STEP)):
        antes = len(world.enemy_bullets)
        world.update(pilot_intent(world.steps))
        states = {id(e): rafaga(e).state for e in world.enemies}
        for key, state in states.items():
            historia[key].append(state)
        if len(world.enemy_bullets) > antes:
            assert VolleyState.FIRING in states.values()
    aviso = round(VOLLEY.telegraph / STEP)
    for states in historia.values():
        runs = [(state, len(list(run))) for state, run in groupby(states)]
        for k, (state, _) in enumerate(runs):
            if state is VolleyState.FIRING:
                assert k > 0
                assert runs[k - 1] == (VolleyState.TELEGRAPHING, aviso)


def rafaga(enemy: Enemy) -> Volley:
    action = enemy.actions[0]
    assert isinstance(action, Volley)
    return action
