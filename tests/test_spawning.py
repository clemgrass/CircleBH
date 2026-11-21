"""Tests de la aparición: el cuadrante más vacío, las formaciones y la cola (ADR 0025)."""

import itertools
import random

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pygame.math import Vector2

from circlebh.balance import BALANCE
from circlebh.world.spawning import (
    FORMATIONS,
    SpawnQueue,
    emptiest_quadrants,
    place_formation,
    quadrant,
)

SPAWNING = BALANCE.spawning
REACH = BALANCE.charges.core_reach
RADIO = BALANCE.enemies["hexagon"].radius
NUCLEO = REACH * 2 * RADIO
"""Dos hexágonos más cerca que esto se empujan con el núcleo duro (`charges.py`)."""


def colocar(kind: str, count: int, ocupados: list[Vector2], seed: int) -> list[Vector2]:
    """Una formación de hexágonos, con otros hexágonos en `ocupados`."""
    return place_formation(
        kind,
        count,
        RADIO,
        [(o, RADIO) for o in ocupados],
        SPAWNING,
        REACH,
        random.Random(seed),
    )


def conteo(ocupados: list[Vector2]) -> list[int]:
    """Cuántos hay en cada cuadrante, contados a mano por los signos."""
    cuenta = [0, 0, 0, 0]
    for p in ocupados:
        cuenta[quadrant(p)] += 1
    return cuenta


formaciones = st.sampled_from(FORMATIONS).flatmap(
    lambda kind: st.tuples(
        st.just(kind), st.just(1) if kind == "single" else st.integers(1, 6)
    )
)
"""Una formación y su tamaño: `single` es siempre de a uno."""
semillas = st.integers(0, 2**32 - 1)
ocupados_al_azar = st.lists(
    st.builds(
        Vector2,
        st.floats(-1500, 1500, allow_nan=False),
        st.floats(-1500, 1500, allow_nan=False),
    ),
    max_size=30,
)


# --- Los cuadrantes ---


@pytest.mark.parametrize(
    ("punto", "esperado"),
    [
        # Sobre un eje: el cuadrante que empieza en ese eje, antihorario desde +x.
        ((1, 0), 0),
        ((0, 1), 1),
        ((-1, 0), 2),
        ((0, -1), 3),
        # Dentro de cada cuadrante.
        ((1, 1), 0),
        ((-1, 1), 1),
        ((-1, -1), 2),
        ((1, -1), 3),
        # Borde: el jugador mismo no tiene dirección; va al 0.
        ((0, 0), 0),
    ],
)
def test_cuadrante_de_cada_eje(punto: tuple[float, float], esperado: int) -> None:
    assert quadrant(Vector2(punto)) == esperado


def test_cuadrantes_mas_vacios() -> None:
    ocupados = [Vector2(1, 1), Vector2(2, 1), Vector2(-1, 1), Vector2(-1, -1)]
    assert emptiest_quadrants(ocupados) == [3]


def test_sin_nadie_todos_empatan() -> None:
    assert emptiest_quadrants([]) == [0, 1, 2, 3]


@given(formacion=formaciones, ocupados=ocupados_al_azar, seed=semillas)
def test_aparece_en_un_cuadrante_mas_vacio(
    formacion: tuple[str, int], ocupados: list[Vector2], seed: int
) -> None:
    # Toda la formación cae en un mismo cuadrante, y es uno de los que tienen menos.
    posiciones = colocar(*formacion, ocupados, seed)
    cuenta = conteo(ocupados)
    [elegido] = {quadrant(p) for p in posiciones}
    assert cuenta[elegido] == min(cuenta)


def test_empate_lo_decide_la_semilla() -> None:
    # Sin nadie, los cuatro empatan: la semilla elige, y con la misma semilla, igual.
    elegidos = {quadrant(colocar("single", 1, [], seed)[0]) for seed in range(40)}
    assert elegidos == {0, 1, 2, 3}
    assert colocar("ring", 4, [], 7) == colocar("ring", 4, [], 7)


# --- Las formaciones ---


@given(formacion=formaciones, ocupados=ocupados_al_azar, seed=semillas)
def test_nadie_aparece_cerca_del_jugador(
    formacion: tuple[str, int], ocupados: list[Vector2], seed: int
) -> None:
    # Negativo: ningún miembro queda a menos de `spawning.distance`, fuera de la vista.
    posiciones = colocar(*formacion, ocupados, seed)
    assert all(p.length() >= SPAWNING.distance - 1e-9 for p in posiciones)


@given(formacion=formaciones, seed=semillas)
def test_formacion_no_nace_encimada(formacion: tuple[str, int], seed: int) -> None:
    # Foco 5: si dos miembros nacen dentro del núcleo duro, el enjambre explota en el
    # primer paso.
    posiciones = colocar(*formacion, [], seed)
    assert len(posiciones) == formacion[1]
    for a, b in itertools.combinations(posiciones, 2):
        assert a.distance_to(b) > NUCLEO


@given(formacion=formaciones, ocupados=ocupados_al_azar, seed=semillas)
def test_formacion_no_nace_encima_de_otro(
    formacion: tuple[str, int], ocupados: list[Vector2], seed: int
) -> None:
    # Decisión 27: tampoco encima de un vivo o de uno que espera en la cola.
    posiciones = colocar(*formacion, ocupados, seed)
    for p, o in itertools.product(posiciones, ocupados):
        assert p.distance_to(o) > NUCLEO


def test_ocupado_corre_la_formacion_hacia_afuera() -> None:
    # Con el mismo azar, un hexágono justo donde iba a nacer el single lo corre hacia
    # afuera, en la misma dirección. Los otros tres, lejos y uno por cuadrante, dejan
    # el empate igual que sin nadie, así que la semilla elige el mismo cuadrante.
    libre = colocar("single", 1, [], 3)[0]
    lejanos = [
        Vector2(5000, 1),
        Vector2(-1, 5000),
        Vector2(-5000, -1),
        Vector2(1, -5000),
    ]
    otros = [p for p in lejanos if quadrant(p) != quadrant(libre)]
    corrido = colocar("single", 1, [libre, *otros], 3)[0]
    assert corrido.length() > libre.length()
    assert corrido.normalize().angle_to(libre.normalize()) == pytest.approx(0, abs=1e-6)


def test_anillo_a_la_distancia_de_aparicion() -> None:
    # El anillo es un arco a `spawning.distance`, con vecinos separados por igual.
    anillo = colocar("ring", 5, [], 1)
    assert [p.length() for p in anillo] == pytest.approx([SPAWNING.distance] * 5)
    pasos = [a.distance_to(b) for a, b in itertools.pairwise(anillo)]
    assert pasos == pytest.approx([pasos[0]] * 4)


def test_fila_perpendicular_al_jugador() -> None:
    # La fila es perpendicular a la dirección al jugador: su punto medio mira a él.
    fila = colocar("line", 3, [], 1)
    medio = fila[1]
    assert (fila[2] - fila[0]).dot(medio) == pytest.approx(0, abs=1e-6)
    assert medio.length() == pytest.approx(SPAWNING.distance)


@pytest.mark.parametrize(
    ("kind", "count", "campo"), [("rombo", 3, "rombo"), ("single", 2, "single")]
)
def test_formacion_invalida_falla(kind: str, count: int, campo: str) -> None:
    # Negativo: una formación que no existe, o un `single` de más de uno.
    with pytest.raises(ValueError, match=campo):
        colocar(kind, count, [], 1)


@pytest.mark.parametrize(
    ("kind", "radio"),
    [
        # El anillo de 6 mide 6 separaciones de arco: más de 90°.
        ("ring", 300.0),
        # Una cuerda más larga que el diámetro no existe.
        ("ring", 700.0),
        ("line", 300.0),
        ("cluster", 2000.0),
    ],
)
def test_formacion_que_no_cabe_en_un_cuadrante_falla(kind: str, radio: float) -> None:
    # Negativo: una formación más ancha que su cuadrante se saldría de él.
    with pytest.raises(ValueError, match="cuadrante"):
        place_formation(kind, 6, radio, [], SPAWNING, REACH, random.Random(1))


# --- La cola ---


def test_cola_sale_en_orden_y_de_a_limite() -> None:
    cola = SpawnQueue()
    cola.push((f"e{k}", Vector2(k, 0)) for k in range(10))
    tandas = [cola.pop(4) for _ in range(4)]
    assert [len(t) for t in tandas] == [4, 4, 2, 0]
    assert [nombre for t in tandas for nombre, _ in t] == [f"e{k}" for k in range(10)]


def test_cola_cuenta_lo_que_espera() -> None:
    cola = SpawnQueue()
    cola.push([("a", Vector2(1, 0)), ("b", Vector2(0, 1))])
    cola.pop(1)
    assert list(cola) == [("b", Vector2(0, 1))]


def test_limite_cero_no_saca_nada() -> None:
    # Borde.
    cola = SpawnQueue()
    cola.push([("a", Vector2(1, 0))])
    assert cola.pop(0) == []
    assert len(list(cola)) == 1
