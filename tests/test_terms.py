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
from circlebh.world.terms import (
    advance_at,
    projectile_offset,
    samples_for,
    trace_points,
)

POINT = BALANCE.weapons["point"]
TIEMPOS = st.floats(min_value=0, max_value=10, allow_nan=False)
# El círculo: un trazo polar que crece a 90 por segundo hasta 320.
CIRCLE = replace(
    POINT,
    kind="trace",
    frame="polar",
    advance=AdvanceSpec(coefficient=90.0, degree=1),
    reach=320.0,
)
ARMONICOS = st.lists(
    st.builds(
        HarmonicSpec,
        amplitude=st.floats(min_value=-40, max_value=40),
        k=st.integers(min_value=0, max_value=8).map(float),
        phase=st.floats(min_value=-math.pi, max_value=math.pi),
    ),
    max_size=3,
).map(tuple)
GIROS = st.floats(min_value=-3, max_value=3)


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


# --- El trazo polar ---


@given(TIEMPOS, ARMONICOS, GIROS, st.integers(min_value=1, max_value=200))
def test_trazo_polar_sigue_su_formula(
    t: float, armonicos: tuple[HarmonicSpec, ...], giro: float, muestras: int
) -> None:
    # `ρ(θ, t) = min(a(t), R) + Σ A·sin(k(θ − Ωt) + φ)`, con θ repartido en la vuelta.
    spec = replace(CIRCLE, harmonics=armonicos, spin=giro)
    puntos = trace_points(spec, t, muestras)
    assert len(puntos) == muestras
    for i, punto in enumerate(puntos):
        theta = 2 * math.pi * i / muestras
        rho = min(90.0 * t, 320.0) + sum(
            h.amplitude * math.sin(h.k * (theta - giro * t) + h.phase)
            for h in armonicos
        )
        assert punto.x == pytest.approx(rho * math.cos(theta), abs=1e-6)
        assert punto.y == pytest.approx(rho * math.sin(theta), abs=1e-6)


@given(TIEMPOS, ARMONICOS, GIROS, st.floats(min_value=2, max_value=50))
def test_muestras_quedan_a_lo_mas_spacing(
    t: float, armonicos: tuple[HarmonicSpec, ...], giro: float, spacing: float
) -> None:
    # Dos puntos seguidos, también el último y el primero, quedan a lo más `spacing`:
    # así ninguna línea pasa entre dos muestras sin que la crucen.
    spec = replace(CIRCLE, harmonics=armonicos, spin=giro)
    puntos = trace_points(spec, t, samples_for(spec, t, spacing))
    for a, b in zip(puntos, puntos[1:] + puntos[:1], strict=True):
        assert a.distance_to(b) <= spacing + 1e-9


def test_anillo_recien_nacido_es_un_punto() -> None:
    # Borde: en `t = 0` el radio es 0, y basta una muestra, en el centro.
    assert samples_for(CIRCLE, 0.0, 4.0) == 1
    assert trace_points(CIRCLE, 0.0, 1)[0].length() == 0


def test_anillo_no_pasa_de_su_alcance() -> None:
    # Borde: el `min(a(t), R)` deja el último paso en R.
    puntos = trace_points(CIRCLE, 100.0, samples_for(CIRCLE, 100.0, 4.0))
    assert all(p.length() == pytest.approx(320.0) for p in puntos)


@pytest.mark.parametrize("spacing", [0.0, -4.0])
def test_spacing_no_positivo_se_rechaza(spacing: float) -> None:
    # Negativo: sin un espaciado positivo no hay cuántas muestras tomar.
    with pytest.raises(ValueError, match="spacing"):
        samples_for(CIRCLE, 1.0, spacing)
