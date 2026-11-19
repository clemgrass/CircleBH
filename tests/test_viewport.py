"""Tests de la cámara: la cuenta de mundo a pantalla (spec, "Cámara"; ADR 0005)."""

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pygame.math import Vector2

from circlebh.viewport import Viewport

FOV = 720.0
HD = (1280, 720)


# --- Centro e Y invertida ---


def test_centro_va_al_centro_del_area_util() -> None:
    center = Vector2(100, -50)
    assert Viewport(HD, FOV, center).to_screen(center) == (640, 360)


def test_centro_va_al_centro_del_area_util_con_franjas() -> None:
    # Área útil (160, 0, 1280, 720): su centro es (800, 360), no el de la ventana.
    center = Vector2(3, 4)
    assert Viewport((1600, 720), FOV, center).to_screen(center) == (800, 360)


def test_y_mayor_queda_mas_arriba() -> None:
    viewport = Viewport(HD, FOV, Vector2(0, 0))
    _, abajo = viewport.to_screen(Vector2(0, 0))
    _, arriba = viewport.to_screen(Vector2(0, 10))
    assert arriba < abajo


def test_x_mayor_queda_mas_a_la_derecha() -> None:
    viewport = Viewport(HD, FOV, Vector2(0, 0))
    assert viewport.to_screen(Vector2(10, 0))[0] > viewport.to_screen(Vector2(0, 0))[0]


def test_el_plano_se_desplaza_con_el_centro() -> None:
    # El origen queda a la izquierda y abajo de un jugador en (100, 100).
    assert Viewport(HD, FOV, Vector2(100, 100)).to_screen(Vector2(0, 0)) == (540, 460)


# --- Escala y FOV ---


def test_fov_por_defecto_es_un_pixel_por_unidad_en_hd() -> None:
    assert Viewport(HD, FOV, Vector2()).scale == 1


def test_ventana_del_doble_escala_al_doble() -> None:
    assert Viewport((2560, 1440), FOV, Vector2()).scale == 2


@given(
    width=st.integers(min_value=1, max_value=8000),
    height=st.integers(min_value=1, max_value=8000),
    cx=st.floats(min_value=-1e4, max_value=1e4),
    cy=st.floats(min_value=-1e4, max_value=1e4),
)
def test_fov_completo_en_alto(width: int, height: int, cx: float, cy: float) -> None:
    # Con cualquier ventana, el borde de arriba y el de abajo del FOV caen justo en
    # los bordes del área útil.
    center = Vector2(cx, cy)
    viewport = Viewport((width, height), FOV, center)
    _, top, _, area_height = viewport.rect
    _, y_top = viewport.to_screen(center + Vector2(0, FOV / 2))
    _, y_bottom = viewport.to_screen(center - Vector2(0, FOV / 2))
    assert y_top == pytest.approx(top, abs=1e-6)
    assert y_bottom == pytest.approx(top + area_height, abs=1e-6)


@given(
    width=st.integers(min_value=0, max_value=8000),
    height=st.integers(min_value=0, max_value=8000),
)
def test_area_util_cabe_en_la_ventana_y_es_16_9(width: int, height: int) -> None:
    left, top, area_width, area_height = Viewport((width, height), FOV, Vector2()).rect
    assert left >= 0
    assert top >= 0
    assert left + area_width <= width
    assert top + area_height <= height
    # Toca la ventana en un eje, y en el otro es 16:9 con error de redondeo de un píxel.
    assert area_width == width or area_height == height
    assert abs(area_width * 9 - area_height * 16) <= 16


# --- Franjas ---


def test_ventana_16_9_no_tiene_franjas() -> None:
    assert Viewport(HD, FOV, Vector2()).rect == (0, 0, 1280, 720)


def test_ventana_ancha_tiene_franjas_a_los_lados() -> None:
    assert Viewport((1600, 720), FOV, Vector2()).rect == (160, 0, 1280, 720)


def test_ventana_alta_tiene_franjas_arriba_y_abajo() -> None:
    assert Viewport((1280, 1000), FOV, Vector2()).rect == (0, 140, 1280, 720)


def test_ventana_minimizada_no_divide_por_cero() -> None:
    viewport = Viewport((0, 0), FOV, Vector2(5, 5))
    assert viewport.rect == (0, 0, 0, 0)
    assert viewport.scale == 0
    assert viewport.to_screen(Vector2(100, 100)) == (0, 0)
    assert viewport.width(1) == 1


# --- Grosores ---


def test_grosor_escala_con_la_camara() -> None:
    assert Viewport((2560, 1440), FOV, Vector2()).width(3) == 6


def test_grosor_minimo_es_un_pixel() -> None:
    # Con 0, pygame.draw.circle rellena el círculo en vez de dibujar su borde.
    viewport = Viewport((640, 360), FOV, Vector2())
    assert viewport.width(0.1) == 1
    assert viewport.width(0) == 1
