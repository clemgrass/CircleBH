"""Tests de la intención de movimiento: teclado, stick y su combinación (spec, "Entrada")."""

import math

import pygame
import pytest
from hypothesis import given
from hypothesis import strategies as st
from pygame.math import Vector2

from circlebh.controls import (
    StickSteps,
    axis_to_unit,
    combine,
    hand_command,
    is_restart,
    keyboard_intent,
    stick_intent,
)

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


# --- Reiniciar ---


def tecla(tipo: int, key: int) -> pygame.event.Event:
    return pygame.event.Event(tipo, key=key)


def boton(button: int) -> pygame.event.Event:
    return pygame.event.Event(pygame.CONTROLLERBUTTONDOWN, instance_id=0, button=button)


def test_r_reinicia() -> None:
    assert is_restart(tecla(pygame.KEYDOWN, pygame.K_r))


@pytest.mark.parametrize(
    "button",
    # A es el de abajo (✕ en PlayStation) y X, el de la izquierda (X en Xbox).
    [pygame.CONTROLLER_BUTTON_A, pygame.CONTROLLER_BUTTON_X],
)
def test_a_y_x_del_control_reinician(button: int) -> None:
    assert is_restart(boton(button))


def test_soltar_r_no_reinicia() -> None:
    # Borde: cuenta el apretar, no el soltar; si no, reiniciaría dos veces.
    assert not is_restart(tecla(pygame.KEYUP, pygame.K_r))


@pytest.mark.parametrize(
    "evento",
    [
        tecla(pygame.KEYDOWN, pygame.K_w),
        boton(pygame.CONTROLLER_BUTTON_B),
        pygame.event.Event(
            pygame.CONTROLLERBUTTONUP, instance_id=0, button=pygame.CONTROLLER_BUTTON_A
        ),
    ],
)
def test_otras_entradas_no_reinician(evento: pygame.event.Event) -> None:
    assert not is_restart(evento)


# --- La mano ---


@pytest.mark.parametrize(
    ("key", "orden"),
    [
        (pygame.K_LEFT, "left"),
        (pygame.K_a, "left"),
        (pygame.K_RIGHT, "right"),
        (pygame.K_d, "right"),
        (pygame.K_UP, "flip_up"),
        (pygame.K_w, "flip_up"),
        (pygame.K_DOWN, "flip_down"),
        (pygame.K_s, "flip_down"),
        (pygame.K_RETURN, "choose"),
        (pygame.K_KP_ENTER, "choose"),
        (pygame.K_r, "reroll"),
        (pygame.K_b, "banish"),
    ],
)
def test_teclas_de_la_mano(key: int, orden: str) -> None:
    assert hand_command(tecla(pygame.KEYDOWN, key)) == orden


@pytest.mark.parametrize(
    ("button", "orden"),
    [
        (pygame.CONTROLLER_BUTTON_DPAD_LEFT, "left"),
        (pygame.CONTROLLER_BUTTON_DPAD_RIGHT, "right"),
        (pygame.CONTROLLER_BUTTON_DPAD_UP, "flip_up"),
        (pygame.CONTROLLER_BUTTON_DPAD_DOWN, "flip_down"),
        (pygame.CONTROLLER_BUTTON_A, "choose"),
        (pygame.CONTROLLER_BUTTON_Y, "reroll"),
        (pygame.CONTROLLER_BUTTON_X, "banish"),
    ],
)
def test_botones_de_la_mano(button: int, orden: str) -> None:
    assert hand_command(boton(button)) == orden


@pytest.mark.parametrize(
    "evento",
    [
        tecla(pygame.KEYUP, pygame.K_RETURN),
        tecla(pygame.KEYDOWN, pygame.K_1),
        boton(pygame.CONTROLLER_BUTTON_B),
        pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(0, 0)),
    ],
)
def test_otras_entradas_no_son_de_la_mano(evento: pygame.event.Event) -> None:
    # Negativo: soltar no cuenta, y no hay atajos 1, 2 y 3 (decisión 8).
    assert hand_command(evento) is None


def eje(axis: int, value: int) -> pygame.event.Event:
    return pygame.event.Event(
        pygame.CONTROLLERAXISMOTION, instance_id=0, axis=axis, value=value
    )


X, Y = pygame.CONTROLLER_AXIS_LEFTX, pygame.CONTROLLER_AXIS_LEFTY


def test_stick_mueve_una_vez_al_cruzar_la_mitad() -> None:
    stick = StickSteps()
    assert stick.command(eje(X, 10000)) is None
    assert stick.command(eje(X, 20000)) == "right"
    # Sigue inclinado: no repite.
    assert stick.command(eje(X, 32767)) is None


def test_stick_vuelve_y_mueve_otra_vez() -> None:
    stick = StickSteps()
    stick.command(eje(X, 30000))
    assert stick.command(eje(X, 0)) is None
    assert stick.command(eje(X, 30000)) == "right"


def test_stick_hacia_la_izquierda_y_en_vertical() -> None:
    stick = StickSteps()
    assert stick.command(eje(X, -30000)) == "left"
    # SDL da la Y positiva hacia abajo.
    assert stick.command(eje(Y, -30000)) == "flip_up"
    assert stick.command(eje(Y, 0)) is None
    assert stick.command(eje(Y, 30000)) == "flip_down"


def test_stick_de_lado_a_lado_mueve_en_cada_cruce() -> None:
    # Borde: pasar de un extremo al otro sin volver al centro también cuenta.
    stick = StickSteps()
    assert stick.command(eje(X, 30000)) == "right"
    assert stick.command(eje(X, -30000)) == "left"


def test_otros_ejes_no_mueven() -> None:
    # Negativo: el stick derecho y los gatillos no son de la mano.
    stick = StickSteps()
    assert stick.command(eje(pygame.CONTROLLER_AXIS_RIGHTX, 30000)) is None
    assert stick.command(tecla(pygame.KEYDOWN, pygame.K_d)) is None
