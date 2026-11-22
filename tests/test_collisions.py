"""Tests de las colisiones: círculos (ADR 0006) y segmentos (ADR 0020)."""

import pytest
from pygame.math import Vector2

from circlebh.world.collisions import (
    circles_touch,
    closest_point_on_segment,
    crossing,
    segment_circle_entry,
    segment_touches_circle,
)


def test_circulos_que_se_tocan() -> None:
    # Los centros a 20 y los radios suman 30: se superponen.
    assert circles_touch(Vector2(0, 0), 12.0, Vector2(20, 0), 18.0)


def test_circulos_tangentes_chocan() -> None:
    # La distancia es exactamente la suma de los radios: 3-4-5, 2 + 3 = 5.
    assert circles_touch(Vector2(1, 1), 2.0, Vector2(4, 5), 3.0)


def test_circulos_separados_no_chocan() -> None:
    # Separados por una unidad: distancia 6, radios que suman 5.
    assert not circles_touch(Vector2(0, 0), 2.0, Vector2(0, -6), 3.0)


def test_un_circulo_dentro_de_otro_choca() -> None:
    # Mismo centro: la distancia 0 no es un caso especial.
    assert circles_touch(Vector2(5, 5), 1.0, Vector2(5, 5), 10.0)


# --- Tramo contra segmento ---


def test_tramo_que_cruza_da_su_t() -> None:
    # El tramo horizontal de x=0 a x=10 cruza el segmento vertical x=4 a 4/10 del camino.
    t = crossing(Vector2(0, 0), Vector2(10, 0), Vector2(4, -5), Vector2(4, 5))
    assert t == pytest.approx(0.4)


def test_tramo_que_termina_sobre_el_segmento_cruza() -> None:
    t = crossing(Vector2(0, 0), Vector2(4, 0), Vector2(4, -5), Vector2(4, 5))
    assert t == pytest.approx(1.0)


def test_tramo_que_toca_el_extremo_del_segmento_cruza() -> None:
    t = crossing(Vector2(0, 5), Vector2(10, 5), Vector2(4, -5), Vector2(4, 5))
    assert t == pytest.approx(0.4)


def test_tramo_paralelo_no_cruza() -> None:
    # Paralelos y colineales dan None: un punto no "cruza" una recta que recorre.
    assert (
        crossing(Vector2(0, 0), Vector2(10, 0), Vector2(0, 1), Vector2(10, 1)) is None
    )
    assert crossing(Vector2(0, 0), Vector2(10, 0), Vector2(2, 0), Vector2(8, 0)) is None


def test_tramo_corto_no_cruza() -> None:
    # Se queda a una unidad del segmento.
    assert crossing(Vector2(0, 0), Vector2(3, 0), Vector2(4, -5), Vector2(4, 5)) is None


def test_tramo_que_pasa_por_fuera_del_segmento_no_cruza() -> None:
    # Cruza la recta del segmento, pero más arriba de su extremo.
    assert (
        crossing(Vector2(0, 6), Vector2(10, 6), Vector2(4, -5), Vector2(4, 5)) is None
    )


# --- Círculo contra segmento ---


def test_punto_mas_cercano_cae_dentro_del_segmento() -> None:
    p = closest_point_on_segment(Vector2(3, 7), Vector2(0, 0), Vector2(10, 0))
    assert p == Vector2(3, 0)


def test_punto_mas_cercano_se_acota_al_extremo() -> None:
    p = closest_point_on_segment(Vector2(-4, 3), Vector2(0, 0), Vector2(10, 0))
    assert p == Vector2(0, 0)
    p = closest_point_on_segment(Vector2(15, -2), Vector2(0, 0), Vector2(10, 0))
    assert p == Vector2(10, 0)


def test_segmento_degenerado() -> None:
    # Negativo: a == b no divide por cero.
    p = closest_point_on_segment(Vector2(3, 4), Vector2(1, 1), Vector2(1, 1))
    assert p == Vector2(1, 1)


def test_circulo_que_corta_el_segmento_lo_toca() -> None:
    assert segment_touches_circle(Vector2(0, 0), Vector2(10, 0), Vector2(5, 2), 3.0)


def test_circulo_tangente_al_segmento_lo_toca() -> None:
    assert segment_touches_circle(Vector2(0, 0), Vector2(10, 0), Vector2(5, 3), 3.0)


def test_circulo_a_una_unidad_del_extremo_no_lo_toca() -> None:
    # Pasado el extremo (10, 0): la distancia es 4 y el radio 3.
    assert not segment_touches_circle(
        Vector2(0, 0), Vector2(10, 0), Vector2(14, 0), 3.0
    )


# --- Dónde entra un tramo a un círculo (el círculo, #59) ---


def test_entrada_al_circulo_desde_afuera() -> None:
    # De x = −10 a x = 10 entra en x = −2: recorrió 8 de 20.
    t = segment_circle_entry(Vector2(-10, 0), Vector2(10, 0), Vector2(), 2.0)
    assert t == pytest.approx(0.4)


def test_tramo_que_empieza_adentro_entra_en_cero() -> None:
    assert segment_circle_entry(Vector2(1, 0), Vector2(10, 0), Vector2(), 2.0) == 0


def test_tramo_que_pasa_afuera_no_entra() -> None:
    assert (
        segment_circle_entry(Vector2(-10, 2.01), Vector2(10, 2.01), Vector2(), 2.0)
        is None
    )


def test_tramo_que_no_alcanza_el_circulo_no_entra() -> None:
    # Va hacia el círculo, pero termina antes: el borde está en x = −2.
    assert segment_circle_entry(Vector2(-10, 0), Vector2(-3, 0), Vector2(), 2.0) is None
