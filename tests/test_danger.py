"""Tests del modo infinito: el presupuesto exponencial y el peligro (spec de la 0.2.0,
"El modo infinito (#65)")."""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from circlebh.balance import EndlessSpec
from circlebh.world.danger import NEUTRAL, Danger, danger_at
from circlebh.world.director import endless_earned

SIN_TOPE = EndlessSpec(
    doubling=4.0, step=0.5, speed_cap=100.0, cadence_cap=100.0, sides_cap=100.0
)
CON_TOPE = EndlessSpec(
    doubling=4.0, step=0.5, speed_cap=1.5, cadence_cap=2.0, sides_cap=2.5
)


# --- El presupuesto ---


@given(x=st.floats(0.0, 50.0))
def test_presupuesto_se_duplica_cada_t(x: float) -> None:
    # La tasa se duplica cada T, así que lo ganado también: E(x + T) = 2·E(x) + E(T).
    t = 4.0
    assert endless_earned(x + t, 3.0, t) == pytest.approx(
        2 * endless_earned(x, 3.0, t) + endless_earned(t, 3.0, t)
    )


def test_presupuesto_parte_en_cero() -> None:
    # Borde: en el compás 0 del infinito todavía no se ganó nada.
    assert endless_earned(0.0, 3.0, 16.0) == 0


# --- El peligro ---


@pytest.mark.parametrize("k", range(5))
def test_peligro_sube_un_escalon_por_duplicacion(k: int) -> None:
    # Con un excedente de B₀·(2^k − 1), el nivel es k: cada duplicación suma `step`.
    base = 3.0
    peligro = danger_at(base * (2**k - 1), base, SIN_TOPE)
    esperado = 1 + 0.5 * k
    assert peligro.speed == pytest.approx(esperado)
    assert peligro.cadence == pytest.approx(esperado)
    assert peligro.sides == pytest.approx(esperado)


def test_multiplicadores_con_tope() -> None:
    # Borde: con un excedente enorme, cada multiplicador se queda en su tope.
    assert danger_at(1e12, 3.0, CON_TOPE) == Danger(speed=1.5, cadence=2.0, sides=2.5)


def test_sin_excedente_es_neutro() -> None:
    # Negativo: sin excedente no hay peligro extra.
    assert danger_at(0.0, 3.0, CON_TOPE) == NEUTRAL
