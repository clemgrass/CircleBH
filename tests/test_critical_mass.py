"""Tests de la masa crítica: el círculo aparece cuando el enjambre se carga hacia un lado
del jugador (spec de la 0.2.0, decisiones 48 a 50)."""

import math
import random
from dataclasses import replace

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pygame.math import Vector2

from circlebh.balance import BALANCE, CriticalMassSpec
from circlebh.world.critical_mass import (
    CriticalMass,
    check_critical_mass,
    mean_resultant_length,
)
from circlebh.world.game import World

SPEC = CriticalMassSpec(enemy="circle", count=4, imbalance=0.5, cooldown_bars=2.0)
BPM = 120.0
"""A 120 bpm un compás dura 2 s: 120 pasos. La espera de 2 compases son 240."""
DE_UN_LADO = [Vector2(100, 0), Vector2(120, 10), Vector2(90, -20), Vector2(150, 5)]
PAREJO = [Vector2(100, 0), Vector2(0, 100), Vector2(-100, 0), Vector2(0, -100)]


# --- La longitud media resultante ---


def test_todos_del_mismo_lado_da_uno() -> None:
    offsets = [Vector2(1, 0), Vector2(5, 0), Vector2(300, 0)]
    assert mean_resultant_length(offsets) == pytest.approx(1.0)


@pytest.mark.parametrize("n", range(2, 13))
def test_repartidos_parejo_da_cero(n: int) -> None:
    offsets = [Vector2(50, 0).rotate_rad(math.tau * k / n) for k in range(n)]
    assert mean_resultant_length(offsets) == pytest.approx(0.0, abs=1e-9)


def test_sin_enemigos_da_cero() -> None:
    assert mean_resultant_length([]) == 0.0


def test_uno_encima_del_jugador_cuenta_sin_direccion() -> None:
    # Dos del mismo lado y uno sin dirección: |2·x̂| / 3.
    offsets = [Vector2(10, 0), Vector2(20, 0), Vector2()]
    assert mean_resultant_length(offsets) == pytest.approx(2 / 3)


@given(
    st.lists(
        st.tuples(
            st.floats(0, math.tau),
            st.floats(1, 1000),
            st.floats(1, 1000),
        ),
        min_size=1,
        max_size=20,
    )
)
def test_no_depende_de_la_distancia(
    enemigos: list[tuple[float, float, float]],
) -> None:
    cerca = [Vector2(d, 0).rotate_rad(a) for a, d, _ in enemigos]
    lejos = [Vector2(d, 0).rotate_rad(a) for a, _, d in enemigos]
    assert mean_resultant_length(cerca) == pytest.approx(
        mean_resultant_length(lejos), abs=1e-9
    )


# --- Cuándo aparece ---


def test_con_masa_critica_de_un_lado_aparece() -> None:
    assert CriticalMass(SPEC, BPM).update(1000, False, DE_UN_LADO) is True


def test_con_uno_menos_no_aparece() -> None:
    assert CriticalMass(SPEC, BPM).update(1000, False, DE_UN_LADO[:3]) is False


def test_repartidos_parejo_no_aparece() -> None:
    assert CriticalMass(SPEC, BPM).update(1000, False, PAREJO * 2) is False


def test_mientras_esta_presente_no_aparece_otro() -> None:
    assert CriticalMass(SPEC, BPM).update(1000, True, DE_UN_LADO) is False


def test_al_matarlo_espera_cooldown_bars() -> None:
    # Muere en el paso 10: puede volver en el paso 250, 2 compases después. Se miran
    # los pasos 249 y 251 para no depender del redondeo justo en el borde.
    masa = CriticalMass(SPEC, BPM)
    masa.update(0, True, DE_UN_LADO)
    assert masa.update(10, False, DE_UN_LADO) is False
    assert masa.update(249, False, DE_UN_LADO) is False
    assert masa.update(251, False, DE_UN_LADO) is True


def test_al_empezar_no_espera() -> None:
    assert CriticalMass(SPEC, BPM).update(0, False, DE_UN_LADO) is True


# --- El balance ---


@pytest.mark.parametrize(
    ("campo", "valor"),
    [
        ("enemy", "nadie"),
        ("count", 0),
        ("imbalance", -0.1),
        ("imbalance", 1.1),
        ("cooldown_bars", -1.0),
    ],
)
def test_rechaza_una_masa_critica_invalida(campo: str, valor: object) -> None:
    malo = replace(
        BALANCE, critical_mass=replace(BALANCE.critical_mass, **{campo: valor})
    )
    with pytest.raises(ValueError, match=rf"critical_mass\.{campo}"):
        World(malo, random.Random(0))


def test_el_balance_real_cumple_la_masa_critica() -> None:
    check_critical_mass(BALANCE)
    assert BALANCE.critical_mass.enemy == "circle"
