"""Tests de las armas por términos: avance, armónicos y giro (ADR 0029).

La posición de lo que dispara un arma es una función pura de su `spec` y del tiempo, en
el marco local del disparo, con `û = (1, 0)`.
"""

import math
from dataclasses import replace

import pytest
from hypothesis import given
from hypothesis import strategies as st

from circlebh.balance import BALANCE, AdvanceSpec, HarmonicSpec
from circlebh.world.terms import advance_at, projectile_offset

POINT = BALANCE.weapons["point"]
TIEMPOS = st.floats(min_value=0, max_value=10, allow_nan=False)


# --- El avance ---


@given(TIEMPOS)
def test_punto_sigue_su_formula(t: float) -> None:
    # El punto del balance: `p(t) = v·t·û`, sin desvío lateral.
    v = POINT.advance.coefficient
    offset = projectile_offset(POINT, t)
    assert offset.x == pytest.approx(v * t)
    assert offset.y == 0


@given(TIEMPOS)
def test_avance_de_grado_cero_queda_quieto(t: float) -> None:
    # Borde: `d/dt` del punto es una mina quieta a `v·τ`, en cualquier `t`.
    mina = replace(POINT, advance=AdvanceSpec(coefficient=300.0, degree=0))
    assert advance_at(mina, t) == pytest.approx(300.0 * mina.tau)


@given(TIEMPOS)
def test_avance_de_grado_dos_acelera(t: float) -> None:
    # `∫dt` del punto: `v·t²/(2τ)`, que parte quieto y acelera.
    acelera = replace(POINT, advance=AdvanceSpec(coefficient=300.0, degree=2))
    assert advance_at(acelera, t) == pytest.approx(300.0 * t * t / (2 * acelera.tau))


def test_sin_avance_no_se_mueve() -> None:
    # Negativo: con `coefficient = 0` no hay avance, en ningún grado.
    for degree in (0, 1, 2):
        quieto = replace(POINT, advance=AdvanceSpec(coefficient=0.0, degree=degree))
        assert advance_at(quieto, 3.0) == 0


def test_rechaza_un_grado_que_no_existe() -> None:
    # Negativo: los grados son 0, 1 y 2; `d/dt` no baja de 0 ni `∫dt` sube de 2.
    raro = replace(POINT, advance=AdvanceSpec(coefficient=300.0, degree=3))
    with pytest.raises(ValueError, match="degree"):
        advance_at(raro, 1.0)


# --- Los armónicos y el marco ---


@given(TIEMPOS)
def test_armonico_cartesiano_desvia_de_lado(t: float) -> None:
    # El seno: `(a(t), A·sin(k·t + φ))`.
    seno = replace(POINT, harmonics=(HarmonicSpec(amplitude=40.0, k=5.0, phase=0.3),))
    offset = projectile_offset(seno, t)
    assert offset.x == pytest.approx(300.0 * t)
    assert offset.y == pytest.approx(40.0 * math.sin(5.0 * t + 0.3), abs=1e-9)


@given(TIEMPOS)
def test_polar_gira_con_su_radio(t: float) -> None:
    # La espiral: `(a(t) + Σ A·sin(k·t + φ))·(cos Ωt, sin Ωt)`.
    espiral = replace(
        POINT,
        frame="polar",
        spin=2.0,
        harmonics=(HarmonicSpec(amplitude=10.0, k=3.0, phase=0.0),),
    )
    r = 300.0 * t + 10.0 * math.sin(3.0 * t)
    offset = projectile_offset(espiral, t)
    assert offset.x == pytest.approx(r * math.cos(2.0 * t), abs=1e-9)
    assert offset.y == pytest.approx(r * math.sin(2.0 * t), abs=1e-9)


def test_polar_sin_giro_es_cartesiano_sin_armonicos() -> None:
    # Borde: sin giro ni armónicos, los dos marcos dan la misma recta.
    polar = replace(POINT, frame="polar")
    assert projectile_offset(polar, 1.5) == projectile_offset(POINT, 1.5)
