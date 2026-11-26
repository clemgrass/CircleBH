"""Tests de los pilotos: el de la demo (P0), una vuelta completa cada 4 s, siempre a
largo 1, y el que esquiva (P1, ADR 0030).

La simulación de 60 s está en `test_simulacion.py`; aquí van los reinicios, con
partidas cortas.
"""

import inspect
import random
import re
from dataclasses import replace

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pygame.math import Vector2

import circlebh.pilot
from circlebh.balance import BALANCE
from circlebh.pilot import (
    DodgingPilot,
    choose_at_random,
    pilot_intent,
    simulate,
    simulate_dodging,
    simulate_worlds,
)
from circlebh.world.enemy import Enemy
from circlebh.world.enemy_bullets import EnemyBullet
from circlebh.world.game import World

STEPS_PER_LAP = 4 * 60


@given(step=st.integers(min_value=0, max_value=10**6))
def test_piloto_tiene_largo_uno(step: int) -> None:
    assert pilot_intent(step).length() == pytest.approx(1)


def test_piloto_parte_hacia_la_derecha() -> None:
    assert pilot_intent(0).x == pytest.approx(1)
    assert pilot_intent(0).y == pytest.approx(0)


def test_piloto_gira_antihorario() -> None:
    # Un cuarto de vuelta después, apunta hacia arriba (+y): ángulo antihorario.
    intent = pilot_intent(STEPS_PER_LAP // 4)
    assert intent.x == pytest.approx(0, abs=1e-9)
    assert intent.y == pytest.approx(1)


def test_piloto_vuelve_al_inicio_tras_4_s() -> None:
    start, lap = pilot_intent(0), pilot_intent(STEPS_PER_LAP)
    assert lap.x == pytest.approx(start.x)
    assert lap.y == pytest.approx(start.y, abs=1e-9)


# --- La simulación ---


def hasta_morir(seed: int) -> float:
    """El oráculo: cuánto dura una partida suelta con `seed`, jugada por el piloto."""
    world = World(BALANCE, random.Random(seed))
    chooser = random.Random(seed)
    while not world.game_over:
        choose_at_random(world, chooser)
        world.update(pilot_intent(world.steps))
    return world.elapsed


def test_simulacion_reinicia_al_morir_con_la_semilla_siguiente() -> None:
    # La partida n usa `seed + n`, como la demo: cada partida terminada dura lo mismo
    # que una suelta con esa semilla. Con las semillas 1 a 4 las duraciones difieren,
    # así que repetir la misma semilla, o sortear otra, no pasa. La intro parte vacía, y
    # una partida dura menos de un minuto: en 120 s caben más de dos.
    durations = simulate(BALANCE, seconds=120.0, seed=1)
    assert len(durations) > 2
    terminadas = durations[:-1]
    assert terminadas == [hasta_morir(1 + n) for n in range(len(terminadas))]


def test_simulacion_corta_la_ultima_partida() -> None:
    durations = simulate(BALANCE, seconds=30.0, seed=1)
    assert sum(durations) == pytest.approx(30.0)


NIVELES_BARATOS = replace(BALANCE, experience=replace(BALANCE.experience, base=0.5))
"""Cada enemigo muerto sube un nivel: la mano sale seguido."""


def test_simulacion_elige_al_subir_de_nivel() -> None:
    # Sin elegir, el mundo se queda detenido en la mano y la partida no suma tiempo.
    # Con la semilla 3, el piloto sube su primer nivel a los 19 s.
    worlds = simulate_worlds(NIVELES_BARATOS, seconds=60.0, seed=3)
    assert max(world.level for world in worlds) > 1
    assert sum(world.elapsed for world in worlds) == pytest.approx(60.0)


def test_simulacion_elige_con_la_semilla_de_la_partida() -> None:
    # La elección sale de una `Random` propia: la misma semilla da la misma partida.
    una = simulate_worlds(NIVELES_BARATOS, seconds=40.0, seed=3)
    otra = simulate_worlds(NIVELES_BARATOS, seconds=40.0, seed=3)
    assert [(w.elapsed, w.loadout) for w in una] == [
        (w.elapsed, w.loadout) for w in otra
    ]


def test_simulacion_sin_peligro_es_una_sola_partida() -> None:
    quietos = {name: replace(spec, speed=0.0) for name, spec in BALANCE.enemies.items()}
    inofensivo = replace(BALANCE, enemies=quietos)
    assert simulate(inofensivo, seconds=5.0, seed=7) == [pytest.approx(5.0)]


# --- P1: el piloto que esquiva (ADR 0030) ---


def mundo_vacio() -> World:
    """Un mundo sin armas ni muerte, en el paso 0: el jugador en el origen y nada más."""
    return World(BALANCE, random.Random(1), lethal=False, armed=False)


def p1(sigma: float = 0.0, seed: int = 1) -> DodgingPilot:
    return DodgingPilot(sigma, random.Random(seed))


def hexagono_en(x: float, y: float) -> Enemy:
    return Enemy(BALANCE.enemies["hexagon"], Vector2(x, y))


def test_p1_huye_del_enemigo() -> None:
    world = mundo_vacio()
    world.enemies = [hexagono_en(100, 0)]
    intent = p1()(world)
    assert intent.x == pytest.approx(-1)
    assert intent.y == pytest.approx(0, abs=1e-9)


def test_p1_la_bala_empuja_desde_donde_va_a_estar() -> None:
    # La bala está a la derecha y baja a 500 u/s: en 0,3 s va a estar en (100, -150).
    # El piloto huye de ese punto, no de donde está ahora.
    world = mundo_vacio()
    world.enemy_bullets = [EnemyBullet(Vector2(100, 0), Vector2(0, -500))]
    intent = p1()(world)
    away = (Vector2() - Vector2(100, -150)).normalize()
    assert intent.x == pytest.approx(away.x)
    assert intent.y == pytest.approx(away.y)


def test_p1_la_bala_empuja_mas_que_el_enemigo() -> None:
    # A la misma distancia, un enemigo a la derecha y una bala quieta arriba: la bala
    # pesa cuatro veces más, así que el piloto huye más hacia abajo que hacia la izq.
    world = mundo_vacio()
    enemy = hexagono_en(100, 0)
    world.enemies = [enemy]
    world.enemy_bullets = [EnemyBullet(Vector2(0, 100 - enemy.radius), Vector2())]
    intent = p1()(world)
    assert intent.y == pytest.approx(4 * intent.x)


def test_p1_gira_la_direccion_con_el_error() -> None:
    # Con σ > 0, la dirección se gira un ángulo, pero sigue de largo 1.
    world = mundo_vacio()
    world.enemies = [hexagono_en(100, 0)]
    intent = p1(sigma=1.2)(world)
    assert intent.length() == pytest.approx(1)
    assert intent != pytest.approx(Vector2(-1, 0))


@pytest.mark.parametrize("sigma", [0.0, 1.2])
def test_p1_sin_enemigos_da_vueltas(sigma: float) -> None:
    # Sin nada que lo empuje, juega como P0 y sin error: el círculo de la demo.
    world = mundo_vacio()
    assert p1(sigma)(world) == pilot_intent(world.steps)


def test_p1_lejos_no_empuja() -> None:
    world = mundo_vacio()
    world.enemies = [hexagono_en(10_000, 0)]
    assert p1()(world) == pilot_intent(world.steps)


def test_p1_enemigo_encima_no_falla() -> None:
    # Un enemigo justo en el centro del jugador no tiene dirección: no empuja. Otro,
    # pegado al jugador, empuja con la distancia mínima y no con 1/0.
    world = mundo_vacio()
    world.enemies = [hexagono_en(0, 0), hexagono_en(1, 0)]
    intent = p1()(world)
    assert intent.x == pytest.approx(-1)


def test_p1_rechaza_sigma_negativo() -> None:
    with pytest.raises(ValueError, match="sigma"):
        p1(sigma=-0.1)


def test_p1_no_saca_numeros_de_la_random_del_mundo() -> None:
    world = mundo_vacio()
    world.enemies = [hexagono_en(100, 0)]
    pilot = p1(sigma=0.6)
    antes = world.rng.getstate()
    # En el paso 0 sortea el error en cada llamada.
    for _ in range(12):
        pilot(world)
    assert world.rng.getstate() == antes


def test_p1_no_usa_la_random_del_mundo() -> None:
    # ADR 0030, Confirmación: una búsqueda de `.rng` en `pilot.py` no encuentra usos
    # del azar del mundo.
    source = inspect.getsource(circlebh.pilot)
    assert re.search(r"\.rng\b", source) is None


def test_p1_determinista() -> None:
    una = simulate_dodging(BALANCE, seconds=30.0, seed=2, sigma=0.6)
    otra = simulate_dodging(BALANCE, seconds=30.0, seed=2, sigma=0.6)
    assert [(w.steps, w.elapsed, w.player.position) for w in una] == [
        (w.steps, w.elapsed, w.player.position) for w in otra
    ]


def test_p1_sigma_cambia_la_partida() -> None:
    # Negativo del anterior: el error sí cambia lo que hace. Si σ no se usara, las dos
    # partidas serían iguales.
    finas = simulate_dodging(BALANCE, seconds=30.0, seed=2, sigma=0.2)
    toscas = simulate_dodging(BALANCE, seconds=30.0, seed=2, sigma=1.2)
    assert finas[0].player.position != toscas[0].player.position


def test_p1_elige_tarjetas_al_subir_de_nivel() -> None:
    worlds = simulate_dodging(NIVELES_BARATOS, seconds=60.0, seed=3, sigma=0.2)
    assert max(world.level for world in worlds) > 1
    assert sum(world.elapsed for world in worlds) == pytest.approx(60.0)
