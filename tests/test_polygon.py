"""Tests del polígono regular: sus vértices, sus aristas y los sectores (ADR 0020)."""

import math

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pygame.math import Vector2

from circlebh.world.collisions import segment_touches_circle
from circlebh.world.polygon import (
    ENVELOPE_SLACK,
    edge_sectors,
    first_hit,
    polygon_edge,
    regular_polygon,
    vertex,
)

R = 24.0
APOTEMA = R * math.cos(math.pi / 6)
"""Distancia del centro del hexágono a cada arista: `R·cos(π/6)`, unos 20,8."""
HEXAGONO = list(range(6))


# --- Vértices ---


@pytest.mark.parametrize("sides", [3, 4, 5, 6])
def test_poligono_tiene_un_vertice_por_lado_sobre_el_circulo(sides: int) -> None:
    centro = Vector2(7, -2)
    vertices = regular_polygon(centro, R, sides)
    assert len(vertices) == sides
    for v in vertices:
        assert v.distance_to(centro) == pytest.approx(R)


def test_poligono_apunta_hacia_arriba() -> None:
    # El primer vértice va arriba (Y positiva, ADR 0003).
    [primero, *_] = regular_polygon(Vector2(0, 0), 10.0, 6)
    assert primero.x == pytest.approx(0, abs=1e-9)
    assert primero.y == pytest.approx(10.0)


def test_poligono_tiene_lados_iguales() -> None:
    vertices = regular_polygon(Vector2(0, 0), 10.0, 6)
    lados = [
        a.distance_to(b)
        for a, b in zip(vertices, vertices[1:] + vertices[:1], strict=True)
    ]
    # En un hexágono regular, el lado mide lo mismo que el radio.
    assert lados == pytest.approx([10.0] * 6)


# --- Aristas ---


@pytest.mark.parametrize("sides", [3, 6])
def test_arista_une_vertices_consecutivos(sides: int) -> None:
    vertices = regular_polygon(Vector2(0, 0), R, sides)
    for k in range(sides):
        a, b = polygon_edge(R, sides, k)
        assert tuple(a) == pytest.approx(tuple(vertices[k]))
        # La última cierra en el vértice 0.
        assert tuple(b) == pytest.approx(tuple(vertices[(k + 1) % sides]))


def test_tramo_por_la_derecha_golpea_la_arista_4() -> None:
    # En el hexágono, la arista 4 va del vértice a 330° al de 30°: la vertical derecha.
    hit = first_hit(Vector2(50, 0), Vector2(10, 0), R, 6, HEXAGONO)
    assert hit is not None
    t, k = hit
    assert k == 4
    assert t == pytest.approx((50 - APOTEMA) / 40)


@pytest.mark.parametrize("vertice", [0, 1])
def test_vertice_da_la_linea_de_indice_menor(vertice: int) -> None:
    # El vértice 0 lo comparten las aristas 5 y 0; el 1, las aristas 0 y 1.
    v = regular_polygon(Vector2(0, 0), R, 6)[vertice]
    hit = first_hit(v * 2, v * 0.5, R, 6, HEXAGONO)
    assert hit is not None
    assert hit[1] == 0


def test_tramo_que_no_cruza_no_golpea() -> None:
    # Pasa por encima del hexágono, que llega hasta y = 24.
    assert first_hit(Vector2(-50, 30), Vector2(50, 30), R, 6, HEXAGONO) is None


def test_bala_desde_adentro_golpea_la_arista_interior() -> None:
    hit = first_hit(Vector2(0, 0), Vector2(50, 0), R, 6, HEXAGONO)
    assert hit is not None
    assert hit[1] == 4


def test_sin_la_arista_de_enfrente_golpea_la_de_atras() -> None:
    # La mecánica de los huecos: sin la arista 4, la bala que viene por la derecha
    # atraviesa el centro y golpea desde adentro la vertical izquierda, la arista 1.
    sin_la_4 = [0, 1, 2, 3, 5]
    hit = first_hit(Vector2(50, 0), Vector2(-50, 0), R, 6, sin_la_4)
    assert hit is not None
    assert hit[1] == 1


def test_sin_aristas_no_golpea() -> None:
    assert first_hit(Vector2(50, 0), Vector2(-50, 0), R, 6, []) is None


# --- Sectores ---


def test_tramo_corto_revisa_pocas_aristas() -> None:
    sectores = edge_sectors(Vector2(30, 1), Vector2(22, 1), 6)
    assert 4 in sectores
    assert len(sectores) <= 3


def test_tramo_por_el_centro_revisa_todas() -> None:
    assert sorted(edge_sectors(Vector2(30, 0), Vector2(-30, 0), 6)) == HEXAGONO


def test_tramo_que_nace_en_el_centro_revisa_todas() -> None:
    assert sorted(edge_sectors(Vector2(0, 0), Vector2(30, 0), 6)) == HEXAGONO


coordenadas = st.floats(min_value=-100, max_value=100)
puntos = st.builds(Vector2, coordenadas, coordenadas)
angulos = st.floats(min_value=0, max_value=math.tau)
largos = st.floats(min_value=0.5, max_value=100)


def direccion(angulo: float) -> Vector2:
    return Vector2(math.cos(angulo), math.sin(angulo))


@st.composite
def tramos(draw: st.DrawFn, sides: int) -> tuple[Vector2, Vector2]:
    """Un tramo cualquiera, o uno dirigido a los casos difíciles de los sectores (la
    revisión de #25 mostró que los puntos al azar casi nunca caen en ellos)."""
    tipo = draw(st.sampled_from(["libre", "vertice", "centro", "arista"]))
    if tipo == "libre":
        return draw(puntos), draw(puntos)
    if tipo == "vertice":
        # Pasa por un vértice, en cualquier dirección: dos aristas empatan.
        v = vertex(R, sides, draw(st.integers(0, sides - 1)))
        d = direccion(draw(angulos))
        return v + d * draw(largos), v - d * draw(largos)
    if tipo == "centro":
        # Pasa por el centro o a menos de 1e-6: el barrido es de casi media vuelta.
        d = direccion(draw(angulos))
        normal = Vector2(-d.y, d.x) * draw(st.floats(-1e-6, 1e-6))
        return d * draw(largos) + normal, -d * draw(largos) + normal
    # Termina justo sobre una arista, en cualquier punto de ella.
    a, b = polygon_edge(R, sides, draw(st.integers(0, sides - 1)))
    return draw(puntos), a + (b - a) * draw(st.floats(0, 1))


@given(sides=st.integers(3, 100), data=st.data())
def test_sectores_dan_lo_mismo_que_todas_las_lineas(
    sides: int, data: st.DataObject
) -> None:
    start, end = data.draw(tramos(sides))
    edges = sorted(data.draw(st.sets(st.integers(0, sides - 1))))
    candidatas = [k for k in edge_sectors(start, end, sides) if k in edges]
    assert first_hit(start, end, R, sides, candidatas) == first_hit(
        start, end, R, sides, edges
    )


@given(sides=st.integers(3, 100), data=st.data())
def test_la_envolvente_no_descarta_golpes(sides: int, data: st.DataObject) -> None:
    start, end = data.draw(tramos(sides))
    # La misma envolvente que usa `Enemy.hit_by`, con su margen.
    if first_hit(start, end, R, sides, range(sides)) is not None:
        assert segment_touches_circle(start, end, Vector2(), R + ENVELOPE_SLACK)
