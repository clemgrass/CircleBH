"""Tests del piloto de la demo: una vuelta completa cada 4 s, siempre a largo 1."""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from circlebh.pilot import pilot_intent

STEPS_PER_LAP = 4 * 60


@given(step=st.integers(min_value=0, max_value=10**6))
def test_piloto_tiene_largo_uno(step: int) -> None:
    assert pilot_intent(step).length() == pytest.approx(1)


def test_piloto_parte_hacia_la_derecha() -> None:
    assert pilot_intent(0).x == pytest.approx(1)
    assert pilot_intent(0).y == pytest.approx(0)


def test_piloto_gira_antihorario() -> None:
    # Un cuarto de vuelta después, apunta hacia arriba (+y): ángulo antihorario.
    intent = pilot_intent(STEPS_PER_LAP // 4)
    assert intent.x == pytest.approx(0, abs=1e-9)
    assert intent.y == pytest.approx(1)


def test_piloto_vuelve_al_inicio_tras_4_s() -> None:
    start, lap = pilot_intent(0), pilot_intent(STEPS_PER_LAP)
    assert lap.x == pytest.approx(start.x)
    assert lap.y == pytest.approx(start.y, abs=1e-9)
