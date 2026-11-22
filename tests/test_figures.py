"""Tests de las figuras: el polígono estrellado `{n/s}` (spec de la 0.2.0, "La estrella").

La estrella chica es `{5/1}` más `{5/2}`: primero sus 5 lados y después sus 5 diagonales.
"""

import math

import pytest
from pygame.math import Vector2

from circlebh.balance import StarPolygonShape
from circlebh.world.figures import check_shape, line_vertices, local_lines
from circlebh.world.polygon import polygon_edge

PHI = (1 + math.sqrt(5)) / 2
ESTRELLA = StarPolygonShape(vertices=5, steps=(1, 2))


def largo(linea: tuple[Vector2, Vector2]) -> float:
    a, b = linea
    return (b - a).length()


# --- La figura ---


@pytest.mark.parametrize("n", range(3, 13))
def test_regular_da_lo_mismo_que_antes(n: int) -> None:
    lineas = local_lines(StarPolygonShape(vertices=n, steps=(1,)), 24.0)
    assert lineas == [polygon_edge(24.0, n, k) for k in range(n)]


def test_estrella_tiene_diez_lineas() -> None:
    assert ESTRELLA.line_count == 10
    assert len(local_lines(ESTRELLA, 40.0)) == 10


def test_diagonal_mide_phi_veces_el_lado() -> None:
    lineas = local_lines(ESTRELLA, 40.0)
    lados, diagonales = lineas[:5], lineas[5:]
    for lado, diagonal in zip(lados, diagonales, strict=True):
        assert largo(diagonal) == pytest.approx(PHI * largo(lado))


def test_pentagrama_une_cada_vertice_con_el_que_esta_dos_mas_alla() -> None:
    pentagrama = StarPolygonShape(vertices=5, steps=(2,))
    assert line_vertices(pentagrama) == [(0, 2), (1, 3), (2, 4), (3, 0), (4, 1)]


# --- El chequeo al cargar ---


def test_rechaza_paso_de_media_vuelta() -> None:
    # En `{6/3}`, la línea 0 y la 3 son la misma: del vértice 0 al 3.
    with pytest.raises(ValueError, match=r"star\.shape"):
        check_shape(StarPolygonShape(vertices=6, steps=(3,)), "star")


def test_rechaza_pasos_repetidos() -> None:
    with pytest.raises(ValueError, match=r"star\.shape"):
        check_shape(StarPolygonShape(vertices=5, steps=(1, 1)), "star")


def test_rechaza_menos_de_tres_vertices() -> None:
    with pytest.raises(ValueError, match=r"star\.shape"):
        check_shape(StarPolygonShape(vertices=2, steps=(1,)), "star")


def test_acepta_la_estrella() -> None:
    check_shape(ESTRELLA, "star")
