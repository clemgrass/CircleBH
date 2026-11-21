"""La armonía: los acordes de la base y su variación con la semilla (ADR 0022).

La armonía la compone una persona: el juego decide cuándo y cuántas notas suenan, pero
solo puede elegirlas del acorde que suena. Por eso la capa del juego nunca desafina.

Las notas se cuentan en semitonos desde La: la raíz del bajo desde La1 (55 Hz) y el
voicing del pad desde La3 (220 Hz).
"""

import random
from dataclasses import dataclass

A1 = 55.0
A3 = 220.0

type Chord = tuple[int, tuple[int, ...]]
"""(raíz del bajo, voicing del pad)."""

CHORDS: tuple[Chord, ...] = (
    (0, (0, 3, 7, 10, 14)),  # Am9
    (-4, (-4, 0, 3, 7, 10)),  # Fmaj9
    (5, (-7, -4, 0, 3, 7)),  # Dm9
    (7, (-5, -2, 2, 5, 10)),  # Em7(11)
)
"""Deep house en La menor: i – VI – iv – v, dos compases cada uno."""

BARS_PER_CHORD = 2


def hz(semitones: float, base: float) -> float:
    """La frecuencia `semitones` semitonos sobre `base`: `base · 2^(n/12)`."""
    return base * 2 ** (semitones / 12)


@dataclass(frozen=True)
class Variation:
    """Cómo suena la base en esta partida: la misma, con otro color."""

    transpose: int
    """Semitonos que se mueve todo: de −5 (Mi menor) a +2 (Si menor)."""
    first_chord: int
    """Con qué acorde de `CHORDS` parte la progresión, de 0 a 3."""


def variation_for(seed: int) -> Variation:
    """La variación de la partida con `seed`.

    Usa un generador propio, nunca la `Random` del mundo: si la música sacara números
    de ahí, la partida cambiaría según si la música suena o no. Con un `str`,
    `random.seed` es determinista entre corridas.
    """
    rng = random.Random(f"musica-{seed}")
    return Variation(transpose=rng.randint(-5, 2), first_chord=rng.randrange(4))


def chord_at(bar: int, variation: Variation) -> Chord:
    """El acorde del compás `bar`, rotado y transpuesto según `variation`."""
    index = (bar // BARS_PER_CHORD + variation.first_chord) % len(CHORDS)
    root, voicing = CHORDS[index]
    shift = variation.transpose
    return root + shift, tuple(note + shift for note in voicing)
