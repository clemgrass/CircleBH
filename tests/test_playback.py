"""Tests de qué hace la reproducción en cada cuadro (ADR 0022).

Reproducen el bug de la música que se callaba a los pocos segundos: en pygame-ce 2.5.8,
si un bloque termina sin otro en cola y justo entonces se encola uno, el callback de fin
de sonido puede dejar el canal mudo con ese bloque atascado en la cola para siempre.
"""

import pytest

from circlebh.audio.playback import PREBUFFER, next_action


def test_canal_mudo_con_un_bloque_atascado_en_la_cola_lo_arranca() -> None:
    # El estado del bug: no suena, pero `get_queue()` devuelve un bloque.
    assert next_action(busy=False, stuck=True, waiting=0) == "play_stuck"
    assert next_action(busy=False, stuck=True, waiting=3) == "play_stuck"


def test_sonando_sin_nada_en_cola_encola_el_siguiente() -> None:
    assert next_action(busy=True, stuck=False, waiting=1) == "queue"


def test_sonando_con_uno_en_cola_espera() -> None:
    # `stuck` solo cuenta sin sonar; sonando, un bloque en cola es lo normal.
    assert next_action(busy=True, stuck=True, waiting=4) == "wait"


@pytest.mark.parametrize("waiting", range(PREBUFFER))
def test_en_silencio_espera_el_colchon_antes_de_partir(waiting: int) -> None:
    assert next_action(busy=False, stuck=False, waiting=waiting) == "wait"


def test_en_silencio_con_el_colchon_lleno_parte() -> None:
    assert PREBUFFER >= 2
    assert next_action(busy=False, stuck=False, waiting=PREBUFFER) == "play"


def test_sonando_sin_bloques_listos_espera() -> None:
    assert next_action(busy=True, stuck=False, waiting=0) == "wait"
