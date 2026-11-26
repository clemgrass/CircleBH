"""Tests del reloj de pasos fijos y de los pasos de captura (ADR 0005)."""

import itertools

from hypothesis import given
from hypothesis import strategies as st

from circlebh.world.clock import FixedStepClock, capture_steps, slowdown_steps


def test_advance_un_paso() -> None:
    assert FixedStepClock().advance(1 / 60) == 1


def test_advance_acumula_el_resto() -> None:
    clock = FixedStepClock()
    assert clock.advance(1 / 120) == 0
    assert clock.advance(1 / 120) == 1


def test_advance_un_cuarto_de_segundo() -> None:
    assert FixedStepClock().advance(0.25) == 15


def test_advance_topa_una_pausa_larga() -> None:
    # Una pausa de 10 s no debe hacer correr 600 pasos de golpe.
    assert FixedStepClock().advance(10) == 15


def test_advance_multiplica_por_la_velocidad_despues_del_tope() -> None:
    # El tope es del tiempo real (ADR 0005): un frame normal a 20× da 20 pasos, no 15.
    assert FixedStepClock().advance(1 / 60, speed=20) == 20
    # Una pausa larga se topa en 0,25 s reales y recién ahí se multiplica: 15 × 2.
    assert FixedStepClock().advance(10, speed=2) == 30


def test_capture_steps_segundos_enteros() -> None:
    assert capture_steps([0, 1, 2]) == [0, 60, 120]


def test_capture_steps_medio_segundo() -> None:
    assert capture_steps([0.5]) == [30]


def test_capture_steps_redondea_al_paso_mas_cercano() -> None:
    # 2,05 s son exactamente 123 pasos, pero 2.05 / (1/60) da 122.99999999999999 en flotante:
    # truncar daría 122.
    assert capture_steps([2.05]) == [123]
    # Un tiempo entre dos pasos va al más cercano.
    assert capture_steps([1 / 60 * 0.4]) == [0]
    assert capture_steps([1 / 60 * 0.6]) == [1]


def test_capture_steps_vacio() -> None:
    assert capture_steps([]) == []


# --- El frenado antes de la mano ---


def test_frenado_da_sus_pasos_en_el_doble_de_tiempo() -> None:
    # Con 12 pasos del mundo, frena hasta quedar quieto en 24 pasos de escena (0,4 s).
    assert slowdown_steps(0, 12) == 0
    assert slowdown_steps(23, 12) < 12
    assert slowdown_steps(24, 12) == 12


def test_frenado_no_pasa_de_sus_pasos() -> None:
    # Negativo: después del frenado, el mundo ya no avanza.
    assert slowdown_steps(1000, 12) == 12


def test_sin_frenado_no_avanza() -> None:
    # Borde: con 0 pasos, la mano sale al tiro.
    assert slowdown_steps(0, 0) == 0
    assert slowdown_steps(5, 0) == 0


@given(n=st.integers(min_value=1, max_value=120))
def test_frenado_nunca_da_mas_de_un_paso_por_escena(n: int) -> None:
    hechos = [slowdown_steps(j, n) for j in range(2 * n + 1)]
    assert all(0 <= b - a <= 1 for a, b in itertools.pairwise(hechos))


@given(n=st.integers(min_value=3, max_value=120))
def test_frenado_espacia_cada_vez_mas_sus_pasos(n: int) -> None:
    # Los pasos de escena en que avanza el mundo quedan cada vez más separados. Caen en
    # pasos enteros, así que un hueco puede quedar uno más corto que el anterior por
    # redondeo, nunca más.
    cuando = [
        j
        for j in range(1, 2 * n + 1)
        if slowdown_steps(j, n) > slowdown_steps(j - 1, n)
    ]
    assert len(cuando) == n
    huecos = [b - a for a, b in itertools.pairwise(cuando)]
    assert all(b >= a - 1 for a, b in itertools.pairwise(huecos))
    assert huecos[-1] > huecos[0]
