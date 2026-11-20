"""Tests de la armonía de la música y de su variación con la semilla (ADR 0022)."""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from circlebh.audio.harmony import (
    A3,
    CHORDS,
    Variation,
    bpm_for,
    chord_at,
    hz,
    variation_for,
)

SIN_VARIAR = Variation(transpose=0, first_chord=0)


def test_hz_una_octava_dobla_la_frecuencia() -> None:
    assert hz(12, A3) == pytest.approx(440.0)
    assert hz(0, A3) == A3


def test_el_acorde_cambia_cada_dos_compases_y_vuelve_en_el_ocho() -> None:
    acordes = [chord_at(bar, SIN_VARIAR) for bar in range(9)]
    assert acordes[0] == acordes[1] == CHORDS[0]
    assert acordes[2] == CHORDS[1]
    assert acordes[6] == acordes[7] == CHORDS[3]
    assert acordes[8] == CHORDS[0]


def test_transponer_mueve_la_raiz_y_el_voicing() -> None:
    root, voicing = CHORDS[0]
    assert chord_at(0, Variation(transpose=-5, first_chord=0)) == (
        root - 5,
        tuple(n - 5 for n in voicing),
    )


def test_el_acorde_inicial_rota_la_progresion() -> None:
    variation = Variation(transpose=0, first_chord=2)
    assert chord_at(0, variation) == CHORDS[2]
    assert chord_at(4, variation) == CHORDS[0]


# --- La variación con la semilla ---


def test_misma_semilla_misma_variacion_y_tempo() -> None:
    assert variation_for(42) == variation_for(42)
    assert bpm_for(42) == bpm_for(42)


@given(st.integers(0, 2**32 - 1))
def test_la_variacion_queda_en_sus_rangos(seed: int) -> None:
    variation = variation_for(seed)
    assert -5 <= variation.transpose <= 2
    assert 0 <= variation.first_chord <= 3
    assert 120 <= bpm_for(seed) <= 126


def test_muchas_semillas_dan_variedad() -> None:
    variaciones = [variation_for(seed) for seed in range(200)]
    assert len({v.transpose for v in variaciones}) >= 4
    assert {v.first_chord for v in variaciones} == {0, 1, 2, 3}
    assert len({bpm_for(seed) for seed in range(200)}) >= 4
