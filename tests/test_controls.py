"""Tests de la intención de movimiento: teclado, stick y su combinación (spec, "Entrada")."""

import math

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pygame.math import Vector2

from circlebh.controls import axis_to_unit, combine, keyboard_intent, stick_intent

DEADZONE = 0.2


# --- Teclado ---


def test_tecla_arriba_es_y_positiva() -> None:
    assert keyboard_intent(left=False, right=False, up=True, down=False) == Vector2(
        0, 1
    )


def test_diagonal_del_teclado_igual_de_rapida() -> None:
    intent = keyboard_intent(left=False, right=True, up=True, down=False)
    assert intent.length() == pytest.approx(1)
    assert intent.x == pytest.approx(intent.y)


def test_teclas_opuestas_se_anulan() -> None:
    assert keyboard_intent(left=True, right=True, up=True, down=True) == Vector2(0, 0)


def test_sin_teclas_no_mueve() -> None:
    assert keyboard_intent(left=False, right=False, up=False, down=False) == Vector2()


# --- Eje del control ---


def test_eje_en_los_extremos() -> None:
    assert axis_to_unit(32767) == 1
    assert axis_to_unit(0) == 0


def test_eje_negativo_no_pasa_de_menos_uno() -> None:
    # El rango de SDL es asimétrico: −32768 dividido por 32767 daría un poco menos de −1.
    assert axis_to_unit(-32768) == -1


# --- Stick ---


def test_stick_arriba_es_y_positiva() -> None:
    # pygame da el eje Y del stick positivo hacia abajo; world usa Y hacia arriba.
    assert stick_intent(0, -1, DEADZONE) == Vector2(0, 1)


def test_stick_en_zona_muerta_no_mueve() -> None:
    assert stick_intent(0.1, 0.1, DEADZONE) == Vector2(0, 0)


def test_stick_justo_en_el_borde_de_la_zona_muerta_no_mueve() -> None:
    assert stick_intent(DEADZONE, 0, DEADZONE) == Vector2(0, 0)


def test_stick_reescala_desde_el_borde_de_la_zona_muerta() -> None:
    # A medio camino entre la zona muerta (0,2) y el tope (1), el largo es 0,5.
    assert stick_intent(0.6, 0, DEADZONE).length() == pytest.approx(0.5)


def test_stick_en_la_esquina_se_recorta_a_uno() -> None:
    # Algunos sticks llegan a (1, 1) en la esquina: largo √2 sin recortar.
    assert stick_intent(1, 1, DEADZONE).length() == pytest.approx(1)


def test_zona_muerta_cero_deja_pasar_todo() -> None:
    assert stick_intent(0.05, 0, 0).length() == pytest.approx(0.05)


@given(
    x=st.floats(min_value=-1, max_value=1),
    y=st.floats(min_value=-1, max_value=1),
    deadzone=st.floats(min_value=0, max_value=0.9),
)
def test_stick_siempre_entre_cero_y_uno(x: float, y: float, deadzone: float) -> None:
    length = stick_intent(x, y, deadzone).length()
    assert 0 <= length <= 1 + 1e-9


@given(
    x=st.floats(min_value=-1, max_value=1),
    y=st.floats(min_value=-1, max_value=1),
)
def test_stick_conserva_la_direccion(x: float, y: float) -> None:
    intent = stick_intent(x, y, DEADZONE)
    if intent.length() > 0:
        assert math.atan2(intent.y, intent.x) == pytest.approx(math.atan2(-y, x))


# --- Combinación ---


def test_intencion_sin_control_usa_solo_el_teclado() -> None:
    keys = keyboard_intent(left=True, right=False, up=False, down=False)
    assert combine(keys) == keys


def test_teclado_y_stick_juntos_no_pasan_de_uno() -> None:
    assert combine(Vector2(1, 0), Vector2(0, 1)).length() == pytest.approx(1)


def test_combinar_nada_es_cero() -> None:
    assert combine() == Vector2(0, 0)
