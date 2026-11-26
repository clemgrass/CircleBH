"""La música de la mano: lo que suena mientras eliges una tarjeta (spec de la 0.3.0,
decisión 16).

Es sencilla a propósito, para cruzarse con el tema sin chocar:
- **la misma armonía:** sigue la progresión del tema desde el compás que sonaba, con
  su variación, así que está en la misma tonalidad;
- **el mismo tempo,** con un arpegio en corcheas de las notas del acorde, una octava
  arriba del pad, que va de un lado al otro;
- **un pad sostenido,** de senos suaves;
- **sin batería:** sin golpes, el pulso del tema no choca con el suyo al volver.

Todo sale de un estado que avanza muestra a muestra (las fases y las envolventes), así
que pedirla de a trozos da lo mismo que pedirla entera.
"""

import math

from circlebh.audio.harmony import A3, Chord, Variation, chord_at, hz
from circlebh.audio.rhythm import RATE, SIXTEENTHS, Grid

PAD_GAIN = 0.063
"""El volumen de cada voz del pad. Son cinco. Con el arpegio, la mano queda unos 5 dB
más suave que el tema: calma, sin sentirse como un hueco."""
PAD_SECOND = 0.3
"""Cuánto del segundo armónico lleva cada voz: un seno puro sonaría hueco."""
ARP_GAIN = 0.22
"""El volumen de una nota del arpegio, al empezar."""
ARP_EVERY = 2
"""Cada cuántas semicorcheas suena una nota del arpegio: corcheas."""
ARP_OCTAVE = 12
"""Cuántos semitonos sobre el pad va el arpegio."""
ARP_DECAY = 0.35
"""En cuántos segundos una nota del arpegio cae a 1/e."""
ARP_ATTACK = 100
"""Muestras que tarda una nota en subir: sin eso, chasquea."""
ARP_PAN = 0.3
"""Cuánto se corre cada nota hacia su lado: una a la izquierda y la siguiente a la
derecha."""
ARP_LIFE = 5 * ARP_DECAY
"""Después de esto, una nota ya no se oye y se suelta."""


class HandMusic:
    """La música de una mano, desde que empieza el frenado hasta que el cruce de vuelta
    termina."""

    def __init__(self, variation: Variation, bar: int, bpm: float) -> None:
        """`bar` es el compás de la progresión del tema que sonaba (`Sequencer.harmony`):
        la música de la mano sigue desde ahí."""
        self._variation = variation
        self._bar = bar
        self._grid = Grid(bpm)
        self._sample = 0
        self._pad_phases = [0.0] * 5
        self._notes: list[list[float]] = []
        """Las notas del arpegio que suenan: `[fase, paso, envolvente, edad, lado]`."""
        self._next_g = 0
        """La próxima semicorchea en que empieza una nota del arpegio."""

    @property
    def chord(self) -> Chord:
        """El acorde que suena ahora."""
        return self._chord_of(self._sixteenth())

    def render(self, n: int) -> list[tuple[float, float]]:
        """Las `n` muestras estéreo siguientes, en −1..1."""
        out: list[tuple[float, float]] = []
        end = self._sample + n
        while self._sample < end:
            g = self._sixteenth()
            # Un tramo por semicorchea: dentro de él no cambia el acorde.
            stop = min(end, self._grid.start(g + 1))
            _, voicing = self._chord_of(g)
            if self._next_g <= g:
                self._start_note(self._next_g, voicing)
                self._next_g += ARP_EVERY
            out += self._synthesize(stop - self._sample, voicing)
        return out

    def _sixteenth(self) -> int:
        """La semicorchea en que cae la muestra actual."""
        g = int(self._sample / self._grid.samples)
        while self._grid.start(g + 1) <= self._sample:
            g += 1
        while self._grid.start(g) > self._sample:
            g -= 1
        return g

    def _chord_of(self, g: int) -> Chord:
        return chord_at(self._bar + g // SIXTEENTHS, self._variation)

    def _start_note(self, g: int, voicing: tuple[int, ...]) -> None:
        """Una nota del arpegio: las notas del acorde, de abajo hacia arriba."""
        index = g // ARP_EVERY
        semitones = voicing[index % len(voicing)] + ARP_OCTAVE
        side = ARP_PAN if index % 2 else -ARP_PAN
        self._notes.append([0.0, hz(semitones, A3) / RATE, 1.0, 0.0, side])

    def _synthesize(
        self, count: int, voicing: tuple[int, ...]
    ) -> list[tuple[float, float]]:
        """`count` muestras del pad y el arpegio, con el acorde `voicing`."""
        sin, tau, tanh = math.sin, math.tau, math.tanh
        steps = [hz(note, A3) / RATE for note in voicing]
        phases = self._pad_phases
        decay = math.exp(-1 / (ARP_DECAY * RATE))
        out = []
        for _ in range(count):
            pad = 0.0
            for v, step in enumerate(steps):
                phases[v] = (phases[v] + step) % 1.0
                pad += sin(tau * phases[v]) + PAD_SECOND * sin(2 * tau * phases[v])
            pad *= PAD_GAIN
            left = right = pad
            for note in self._notes:
                note[0] = (note[0] + note[1]) % 1.0
                attack = min(1.0, note[3] / ARP_ATTACK)
                x = sin(tau * note[0]) * note[2] * attack * ARP_GAIN
                left += x * (1 - note[4])
                right += x * (1 + note[4])
                note[2] *= decay
                note[3] += 1
            out.append((tanh(left), tanh(right)))
        self._sample += count
        self._notes = [n for n in self._notes if n[3] < ARP_LIFE * RATE]
        return out
