"""Los sonidos de la música, sintetizados con código (ADR 0022).

Cada función devuelve un sonido mono como `array("d")`, con valores cerca de [−1, 1], y
se calcula una sola vez: queda en caché. Los que llevan ruido usan su propia `Random`
de semilla fija, así que no dependen del orden en que se generan ni tocan el azar del
juego.

El timbre de un polígono sale de su forma: un punto recorre las aristas que le quedan a
rapidez constante, y su `x` es la onda. Entero, el hexágono suena suave (armónicos en
k = 1 ± 6m, con magnitud 1/k²); con huecos, el punto salta y suena más brillante.
"""

import math
import random
from array import array
from functools import cache, lru_cache

from circlebh.audio.harmony import A3, hz
from circlebh.audio.rhythm import RATE
from circlebh.world.polygon import polygon_edge

TABLE = 2048
"""Muestras de un ciclo de onda de un polígono."""

type Samples = array[float]


def lowpass(xs: list[float], cutoff: float) -> list[float]:
    """Un pasa-bajos de un polo: `y += a·(x − y)`, con `a = 1 − e^(−2π·fc/RATE)`."""
    a = 1 - math.exp(-math.tau * cutoff / RATE)
    y, out = 0.0, []
    for x in xs:
        y += a * (x - y)
        out.append(y)
    return out


def _samples(xs: list[float]) -> Samples:
    return array("d", xs)


# --- La batería ---


@cache
def kick() -> Samples:
    """Una seno que cae de 185 a 45 Hz en unos 25 ms, saturada, más un click de ruido."""
    rng = random.Random(1)
    out, phase = [], 0.0
    for i in range(int(0.4 * RATE)):
        t = i / RATE
        phase += math.tau * (45 + 140 * math.exp(-t / 0.025)) / RATE
        click = rng.uniform(-1, 1) * math.exp(-t / 0.002) * 0.3
        out.append(math.tanh(1.6 * math.sin(phase) * math.exp(-t / 0.16)) + click)
    return _samples(out)


def _hat(seed: int, decay: float, length: float) -> Samples:
    """Ruido blanco con un pasa-altos simple, `x[n] − x[n−1]`, y caída exponencial."""
    rng = random.Random(seed)
    out, prev = [], 0.0
    for i in range(int(length * RATE)):
        n = rng.uniform(-1, 1)
        out.append((n - prev) * 0.5 * math.exp(-i / RATE / decay))
        prev = n
    return _samples(out)


@cache
def closed_hat() -> Samples:
    return _hat(2, 0.02, 0.1)


@cache
def open_hat() -> Samples:
    return _hat(3, 0.11, 0.5)


@cache
def clap() -> Samples:
    """Tres ráfagas de ruido separadas por 10 ms, más una cola."""
    rng = random.Random(4)
    raw = []
    for i in range(int(0.35 * RATE)):
        t = i / RATE
        env = sum(math.exp(-(t - d) / 0.006) for d in (0, 0.01, 0.021) if t >= d)
        env += 0.7 * math.exp(-t / 0.11)
        raw.append(rng.uniform(-1, 1) * env)
    hp = [raw[0]] + [raw[i] - 0.9 * raw[i - 1] for i in range(1, len(raw))]
    return _samples([v * 0.5 for v in lowpass(hp, 3500)])


@cache
def riser(seconds: float) -> Samples:
    """Ruido que sube durante `seconds`: anuncia que la próxima frase sube."""
    rng = random.Random(5)
    n = int(seconds * RATE)
    out, y = [], 0.0
    for i in range(n):
        u = i / n
        a = 1 - math.exp(-math.tau * (300 + 9000 * u**2) / RATE)
        y += a * (rng.uniform(-1, 1) - y)
        out.append(y * u**2 * 0.8)
    return _samples(out)


@cache
def impact() -> Samples:
    """Un golpe de ruido largo: marca que la música cambia de capa o de partida."""
    rng = random.Random(6)
    out = [
        rng.uniform(-1, 1) * math.exp(-i / RATE / 0.35) * 0.35
        for i in range(int(1.2 * RATE))
    ]
    return _samples(lowpass(out, 6000))


@cache
def rim() -> Samples:
    """El golpe de una bala: un rim corto y seco."""
    rng = random.Random(7)
    out = []
    for i in range(int(0.06 * RATE)):
        t = i / RATE
        tone = math.sin(math.tau * 1700 * t) + 0.5 * rng.uniform(-1, 1)
        out.append(tone * math.exp(-t / 0.008))
    return _samples(out)


# --- Lo que tiene altura ---


def _saw_pluck(freq: float, seconds: float, decay: float) -> list[float]:
    out, phase = [], 0.0
    for i in range(int(seconds * RATE)):
        phase = (phase + freq / RATE) % 1.0
        out.append((2 * phase - 1) * math.exp(-i / RATE / decay))
    return out


@lru_cache(maxsize=64)
def stab(voicing: tuple[int, ...]) -> Samples:
    """Un acorde corto de house, una octava sobre el voicing del pad."""
    n = int(0.3 * RATE)
    out = [0.0] * n
    for semitones in voicing:
        note = _saw_pluck(hz(semitones + 12, A3), 0.3, 0.09)
        for i in range(n):
            out[i] += note[i] / len(voicing)
    return _samples(lowpass(lowpass(out, 2200), 2200))


@lru_cache(maxsize=64)
def blip(freq: float) -> Samples:
    """El arma punto: un pluck corto de diente de sierra."""
    return _samples(lowpass(_saw_pluck(freq, 0.15, 0.04), 2500))


@lru_cache(maxsize=64)
def shape_table(sides: int, edges: tuple[int, ...]) -> Samples:
    """Un ciclo de onda: la `x` de un punto que recorre `edges` a rapidez constante,
    centrada en 0 y con pico 1. Con huecos entre aristas, el punto salta."""
    if not edges:
        raise ValueError("un polígono sin aristas no tiene timbre")
    xs: list[float] = []
    per_edge = TABLE / len(edges)
    for i, k in enumerate(edges):
        a, b = polygon_edge(1.0, sides, k)
        start, end = round(i * per_edge), round((i + 1) * per_edge)
        xs.extend(a.lerp(b, (j - start) / (end - start)).x for j in range(start, end))
    mean = sum(xs) / len(xs)
    peak = max(abs(v - mean) for v in xs) or 1.0
    return _samples([(v - mean) / peak for v in xs])


@lru_cache(maxsize=256)
def poly_note(sides: int, edges: tuple[int, ...], freq: float) -> Samples:
    """La nota de un loop de enemigo: la forma que le queda es el timbre."""
    table = shape_table(sides, edges)
    step = freq * TABLE / RATE
    out, phase = [], 0.0
    for i in range(int(0.22 * RATE)):
        envelope = min(1.0, i / 60) * math.exp(-i / RATE / 0.07)
        out.append(table[int(phase) % TABLE] * envelope)
        phase += step
    return _samples(lowpass(out, 5000))
