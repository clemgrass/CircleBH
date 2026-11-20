"""Tests de la grilla espacial: da los mismos pares que revisar todos contra todos (ADR 0006)."""

import math
from itertools import combinations

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pygame.math import Vector2

from circlebh.world.collisions import circles_touch
from circlebh.world.grid import SpatialGrid

CELDA = 60.0


def fuerza_bruta(
    posiciones: list[Vector2], radios: list[float]
) -> set[tuple[int, int]]:
    """El oráculo: cada par contra todos, con el mismo criterio que el resto del mundo."""
    return {
        (i, j)
        for i, j in combinations(range(len(posiciones)), 2)
        if circles_touch(posiciones[i], radios[i], posiciones[j], radios[j])
    }


# Coordenadas al azar, más puntos justo en los bordes de las celdas (múltiplos de 60),
# que es donde una grilla suele equivocarse.
coordenada = st.one_of(
    st.floats(min_value=-500, max_value=500),
    st.integers(min_value=-8, max_value=8).map(lambda n: n * CELDA),
)
cuerpo = st.tuples(coordenada, coordenada, st.floats(min_value=0, max_value=30))


@given(cuerpos=st.lists(cuerpo, max_size=60))
def test_grilla_igual_a_todos_contra_todos(
    cuerpos: list[tuple[float, float, float]],
) -> None:
    posiciones = [Vector2(x, y) for x, y, _ in cuerpos]
    radios = [r for _, _, r in cuerpos]
    assert SpatialGrid(CELDA).pairs(posiciones, radios) == fuerza_bruta(
        posiciones, radios
    )


def test_tangentes_cuentan_como_par() -> None:
    pares = SpatialGrid(CELDA).pairs([Vector2(0, 0), Vector2(20, 0)], [10.0, 10.0])
    assert pares == {(0, 1)}


def test_lejanos_no_son_par() -> None:
    pares = SpatialGrid(CELDA).pairs([Vector2(0, 0), Vector2(500, 0)], [10.0, 10.0])
    assert pares == set()


def test_celda_chica_da_error() -> None:
    # Con radios de 40, dos que se tocan pueden quedar a dos celdas de 60.
    with pytest.raises(ValueError, match="celda"):
        SpatialGrid(CELDA).pairs([Vector2(0, 0), Vector2(70, 0)], [40.0, 40.0])


def test_posicion_no_finita_da_error_claro() -> None:
    with pytest.raises(ValueError, match="1"):
        SpatialGrid(CELDA).pairs([Vector2(0, 0), Vector2(math.nan, 0)], [5.0, 5.0])
