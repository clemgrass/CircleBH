"""Tests del piloto de la demo: una vuelta completa cada 4 s, siempre a largo 1.

La simulación de 60 s está en `test_simulacion.py`; aquí van los reinicios, con
partidas cortas.
"""

import random
from dataclasses import replace

import pytest
from hypothesis import given
from hypothesis import strategies as st

from circlebh.balance import BALANCE
from circlebh.pilot import (
    choose_at_random,
    pilot_intent,
    simulate,
    simulate_worlds,
)
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
