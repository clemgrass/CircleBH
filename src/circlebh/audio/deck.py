"""La mezcla entre el tema y la música de la mano (spec de la 0.3.0, decisión 16,
enfoque A).

El tema no cambia: `Sequencer` sigue avanzando solo con los pasos del mundo, así que
sigue en sincronía con el director (ADR 0025 y 0026). Lo que cambia es cómo se escucha:
- **la velocidad `rate`:** el tema se lee a la velocidad del mundo. Jugando es 1 y sale
  tal cual. En el frenado baja hasta 0, y el tema baja de tono como un disco que se
  detiene. Con la mano abierta es 0, y el tema queda en pausa donde iba;
- **el cruce:** con la mano, el tema se va en `FADE_IN` y entra la música de la mano;
  al elegir, el tema vuelve desde donde quedó en `FADE_OUT`. El cruce es de potencia
  constante, `cos` y `sin`, para que no baje el volumen a mitad de camino.

Es lógica pura, como el resto de `audio/`: no toca el mixer ni el mundo.
"""

import math
from array import array
from collections import deque

from circlebh.audio.hand_music import HandMusic
from circlebh.audio.harmony import Variation
from circlebh.audio.rhythm import Grid
from circlebh.audio.sequencer import PEAK, SAMPLES_PER_STEP
from circlebh.balance import BALANCE
from circlebh.world.clock import STEP

FADE_IN = 0.4
"""Segundos en que el tema se va hacia la mano: lo que dura el frenado."""
FADE_OUT = 0.5
"""Segundos en que el tema vuelve al elegir."""
BPM = BALANCE.director.bpm
"""El tempo del tema: la música de la mano lo sigue."""
PREFILL = round(Grid(BPM).samples) + 2 * SAMPLES_PER_STEP
"""Muestras del tema que se esperan antes de empezar a leer. El tema llega de a una
semicorchea, y se lee de a un paso: sin este margen, se acabaría justo antes de que
llegue la siguiente."""
OUT_STEPS = 8
"""Cuántos pasos lleva cada bloque que sale: unos 133 ms. Con los 4 que caben en la
cola de `MusicPlayer`, alcanza para medio segundo."""
COMPACT = 1 << 16
"""Cuando lo leído pasa de esto, se suelta: así el tema guardado no crece."""
SNAP = 1e-9
"""Un cruce a menos de esto de su punta queda en la punta: sumar `1/24` veinticuatro
veces no da 1 exacto."""
LIMIT = 32767
"""El tope de una muestra de 16 bits."""


class Deck:
    """Lo que suena: el tema a la velocidad del mundo, cruzado con la música de la mano.

    En cada paso de la escena, `feed` recibe los bloques del tema y `step` mezcla
    `SAMPLES_PER_STEP` muestras. Lo que sale queda en `ready`, como bytes estéreo de 16
    bits, igual que los bloques del tema."""

    def __init__(self) -> None:
        self.ready: deque[bytes] = deque()
        self.fade = 0.0
        """El cruce: 0 es solo el tema, y 1, solo la música de la mano."""
        self._left = array("h")
        self._right = array("h")
        self._pos = 0.0
        """Dónde va la lectura del tema, en muestras. Con `rate` 1 queda entera."""
        self._started = False
        self._hand: HandMusic | None = None
        self._out = array("h")
        self._out_steps = 0

    @property
    def buffered(self) -> int:
        """Las muestras del tema que esperan ser leídas."""
        return len(self._left) - int(self._pos)

    def feed(self, blocks: deque[bytes]) -> None:
        """Saca los bloques del tema de `blocks` y los guarda para leerlos."""
        while blocks:
            samples = array("h")
            samples.frombytes(blocks.popleft())
            self._left += samples[0::2]
            self._right += samples[1::2]

    def step(
        self, rate: float, toward_hand: bool, harmony: tuple[Variation, int]
    ) -> None:
        """Mezcla un paso: el tema leído a `rate`, cruzado hacia la mano si
        `toward_hand`. `harmony` es la de `Sequencer.harmony`: la música de la mano
        parte desde ahí, al empezar el cruce."""
        if toward_hand and self._hand is None:
            self._hand = HandMusic(*harmony, BPM)
        before = self.fade
        self.fade = self._next_fade(toward_hand)
        if not self._started and self.buffered >= PREFILL:
            self._started = True
        n = SAMPLES_PER_STEP
        if before == self.fade == 0 and self._hand is None and rate == 1:
            self._pass_through(n)
        else:
            self._mix(n, before, rate)
        if self.fade == 0 and not toward_hand:
            self._hand = None
        self._out_steps += 1
        if self._out_steps == OUT_STEPS:
            self.ready.append(self._out.tobytes())
            self._out = array("h")
            self._out_steps = 0
        self._compact()

    def _pass_through(self, n: int) -> None:
        """Jugando, sin cruce y a velocidad 1, el tema sale tal cual: se copia el
        tramo entero, sin calcular muestra a muestra. Es casi todo el tiempo."""
        i = int(self._pos)
        if not self._started or i + n >= len(self._left):
            # Sin tema que alcance: el camino lento sabe callar sin repetir muestras.
            self._mix(n, 0.0, 1.0)
            return
        # Después de un frenado, la lectura quedó entre dos muestras. Vuelve a la
        # anterior: retrocede menos de una muestra (23 µs), y no se oye.
        self._pos = float(i)
        chunk = array("h", bytes(4 * n))
        chunk[0::2] = self._left[i : i + n]
        chunk[1::2] = self._right[i : i + n]
        self._out += chunk
        self._pos += n

    def _mix(self, n: int, before: float, rate: float) -> None:
        """`n` muestras, una a una: el tema leído a `rate`, con el cruce yendo de
        `before` a `fade` a lo largo del paso, y la música de la mano si suena."""
        hand = self._hand.render(n) if self._hand is not None else None
        for k in range(n):
            x = before + (self.fade - before) * (k + 1) / n
            theme = math.cos(math.pi / 2 * x)
            left, right = self._read(rate)
            left, right = left * theme, right * theme
            if hand is not None:
                mine = math.sin(math.pi / 2 * x) * PEAK
                left += hand[k][0] * mine
                right += hand[k][1] * mine
            self._out.append(_clip(left))
            self._out.append(_clip(right))

    def _next_fade(self, toward_hand: bool) -> float:
        if toward_hand:
            fade = self.fade + STEP / FADE_IN
            return 1.0 if fade > 1 - SNAP else fade
        fade = self.fade - STEP / FADE_OUT
        return 0.0 if fade < SNAP else fade

    def _read(self, rate: float) -> tuple[float, float]:
        """La muestra del tema en la lectura, y avanza `rate`.

        Entre dos muestras, interpola en línea recta: así, a menos de 1, el tema se
        estira y baja de tono. Con `rate` 0 el disco está quieto, y no suena: una
        muestra repetida sería un zumbido. Si el tema no alcanzó a llegar, sale
        silencio y la lectura espera, sin repetir muestras."""
        i = int(self._pos)
        if not self._started or rate <= 0 or i + 1 >= len(self._left):
            return 0.0, 0.0
        frac = self._pos - i
        left = self._left[i] + (self._left[i + 1] - self._left[i]) * frac
        right = self._right[i] + (self._right[i + 1] - self._right[i]) * frac
        self._pos += rate
        return left, right

    def _compact(self) -> None:
        """Suelta lo ya leído."""
        done = int(self._pos)
        if done > COMPACT:
            del self._left[:done]
            del self._right[:done]
            self._pos -= done


def _clip(x: float) -> int:
    return max(-LIMIT, min(LIMIT, round(x)))
