"""Tests de la música de la mano: un pad y un arpegio con la progresión del tema, sin
batería (spec de la 0.3.0, decisión 16)."""

import math

from hypothesis import given, settings
from hypothesis import strategies as st

from circlebh.audio.hand_music import HandMusic
from circlebh.audio.harmony import BARS_PER_CHORD, Variation, chord_at
from circlebh.audio.rhythm import RATE, SIXTEENTHS, Grid

BPM = 124.0
VARIACION = Variation(transpose=-2, first_chord=1)
COMPAS = round(SIXTEENTHS * Grid(BPM).samples)
"""Muestras de un compás."""


def test_misma_armonia_mismo_sonido() -> None:
    una = HandMusic(VARIACION, 3, BPM).render(RATE)
    otra = HandMusic(VARIACION, 3, BPM).render(RATE)
    assert una == otra


@settings(max_examples=20, deadline=None)
@given(
    transpose=st.integers(min_value=-5, max_value=2),
    first=st.integers(min_value=0, max_value=3),
    bar=st.integers(min_value=0, max_value=40),
)
def test_mano_no_satura(transpose: int, first: int, bar: int) -> None:
    musica = HandMusic(Variation(transpose, first), bar, BPM)
    muestras = musica.render(RATE // 2)
    assert all(-1 <= x <= 1 for frame in muestras for x in frame)
    rms = math.sqrt(sum(left * left for left, _ in muestras) / len(muestras))
    assert rms > 0.01


def test_mano_sigue_la_progresion() -> None:
    musica = HandMusic(VARIACION, 3, BPM)
    assert musica.chord == chord_at(3, VARIACION)
    musica.render(BARS_PER_CHORD * COMPAS)
    assert musica.chord == chord_at(3 + BARS_PER_CHORD, VARIACION)
    assert musica.chord != chord_at(3, VARIACION)


def test_renderizar_de_a_trozos_da_lo_mismo() -> None:
    # La escena pide un paso por vez: el sonido no depende de cómo se corte.
    entera = HandMusic(VARIACION, 0, BPM).render(3000)
    musica = HandMusic(VARIACION, 0, BPM)
    trozos = musica.render(735) + musica.render(735) + musica.render(1530)
    assert trozos == entera


def test_cero_muestras_no_avanza() -> None:
    # Borde.
    musica = HandMusic(VARIACION, 0, BPM)
    assert musica.render(0) == []
    assert musica.render(10) == HandMusic(VARIACION, 0, BPM).render(10)
