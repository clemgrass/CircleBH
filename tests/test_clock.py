"""Tests del reloj de pasos fijos y de los pasos de captura (ADR 0005)."""

from circlebh.world.clock import FixedStepClock, capture_steps


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
