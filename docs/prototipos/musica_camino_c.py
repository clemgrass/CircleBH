"""Prototipo desechable de la música, camino C (ADR 0022).

Se guarda como referencia para el #44: no es código del juego, no se mantiene ni se
testea, y puede dejar de correr cuando cambie `world/`. Lo que midió está en el ADR 0022,
sección Prototipos.

Una base de techno fija (bombo, bajo con sidechain, pad, hats y frases de 4 compases) y,
encima, la geometría como estructura:

- cada enemigo cercano es un loop euclidiano E(lados, 16) que toca notas del acorde,
  rotado según su ángulo alrededor del jugador; al perder una arista pierde ese golpe;
- el arma punto es un loop E(k, 16), con k = golpes que caben en un compás según su
  `cooldown`, que solo suena si de verdad disparó;
- golpes y muertes son acentos cuantizados.

Saca los eventos comparando un paso con el siguiente. La implementación real los toma
de la lista de eventos de `World` (ADR 0022).

Uso, desde la raíz del repo:

    uv run python -I docs/prototipos/musica_camino_c.py SALIDA.wav \
        [SEGUNDOS] [SEMILLA] [inmortal|-] [todo|base|juego]

`inmortal` hace que el jugador no muera; `base` y `juego` generan solo esa parte.
"""

import hashlib
import math
import random
import statistics
import sys
import time
import wave
from array import array

from circlebh.balance import BALANCE
from circlebh.pilot import pilot_intent
from circlebh.seeds import next_seed
from circlebh.world.clock import STEP
from circlebh.world.game import World
from circlebh.world.polygon import polygon_edge

RATE = 44100
BPM = 124
S16 = RATE * 60 / BPM / 4
"""Muestras por semicorchea. No es entero: la grilla se redondea en cada punto."""
BAR = 16 * S16 / RATE
SWING = round(0.12 * S16)
"""Swing de 56 %: las semicorcheas impares se atrasan un poco."""
PHRASE = 4
"""Compases por frase: las capas solo cambian al empezar una frase."""
LOOKAHEAD = S16
"""El bloque siguiente ya está en cola: un evento suena una semicorchea después, como
mínimo."""
MAX_LOOPS = 3
"""Cuántos enemigos tienen loop: los más cercanos. Los demás solo suben la intensidad."""
TABLE = 2048
IMMORTAL = len(sys.argv) > 4 and sys.argv[4] == "inmortal"
MODE = sys.argv[5] if len(sys.argv) > 5 else "todo"
"""'base' (solo la base fija), 'juego' (solo lo que sale del juego) o 'todo'."""
BASE = MODE in ("todo", "base")
GAME = MODE in ("todo", "juego")


def grid(g: int) -> int:
    """Muestra donde empieza la semicorchea `g`."""
    return round(g * S16)


def hz(semis: float, base: float) -> float:
    return base * 2 ** (semis / 12)


def euclid(k: int, n: int) -> list[bool]:
    """E(k, n): k golpes repartidos lo más parejo posible en n pasos (Toussaint 2005)."""
    return [(i * k) % n < k for i in range(n)]


# --- Armonía: deep house en La menor ----------------------------------------------------

A1, A3 = 55.0, 220.0
CHORDS = [
    (0, (0, 3, 7, 10, 14)),  # Am9
    (-4, (-4, 0, 3, 7, 10)),  # Fmaj9
    (5, (-7, -4, 0, 3, 7)),  # Dm9
    (7, (-5, -2, 2, 5, 10)),  # Em7(11)
]
"""(raíz del bajo desde La1, voicing del pad desde La3). Dos compases cada uno."""


def chord_at(bar: int) -> tuple[int, tuple[int, ...]]:
    return CHORDS[(bar // 2) % len(CHORDS)]


# --- Sonidos de un disparo, generados una vez -------------------------------------------

noise = random.Random(7)


def lowpass(xs: list[float], cutoff: float) -> list[float]:
    a = 1 - math.exp(-math.tau * cutoff / RATE)
    y, out = 0.0, []
    for x in xs:
        y += a * (x - y)
        out.append(y)
    return out


def kick() -> list[float]:
    """Una seno que cae de 185 a 45 Hz en unos 25 ms, saturada, más un click de ruido."""
    out, ph = [], 0.0
    for i in range(int(0.4 * RATE)):
        t = i / RATE
        ph += math.tau * (45 + 140 * math.exp(-t / 0.025)) / RATE
        click = noise.uniform(-1, 1) * math.exp(-t / 0.002) * 0.3
        out.append(math.tanh(1.6 * math.sin(ph) * math.exp(-t / 0.16)) + click)
    return out


def hat(decay: float, length: float) -> list[float]:
    """Ruido blanco con un pasa-altos simple, `x[n] − x[n−1]`, y caída exponencial."""
    out, prev = [], 0.0
    for i in range(int(length * RATE)):
        n = noise.uniform(-1, 1)
        out.append((n - prev) * 0.5 * math.exp(-i / RATE / decay))
        prev = n
    return out


def clap() -> list[float]:
    """Tres ráfagas de ruido separadas por 10 ms, más una cola."""
    raw = []
    for i in range(int(0.35 * RATE)):
        t = i / RATE
        env = sum(math.exp(-(t - d) / 0.006) for d in (0, 0.01, 0.021) if t >= d)
        env += 0.7 * math.exp(-t / 0.11)
        raw.append(noise.uniform(-1, 1) * env)
    hp = [raw[0]] + [raw[i] - 0.9 * raw[i - 1] for i in range(1, len(raw))]
    return [v * 0.5 for v in lowpass(hp, 3500)]


def riser() -> list[float]:
    """Ruido que sube durante un compás: anuncia que la próxima frase sube."""
    n = int(BAR * RATE)
    out, y = [], 0.0
    for i in range(n):
        u = i / n
        a = 1 - math.exp(-math.tau * (300 + 9000 * u**2) / RATE)
        y += a * (noise.uniform(-1, 1) - y)
        out.append(y * u**2 * 0.8)
    return out


def impact() -> list[float]:
    out = []
    for i in range(int(1.2 * RATE)):
        t = i / RATE
        out.append(noise.uniform(-1, 1) * math.exp(-t / 0.35) * 0.35)
    return lowpass(out, 6000)


def tick() -> list[float]:
    """El golpe de una bala: un rim corto y seco."""
    out = []
    for i in range(int(0.06 * RATE)):
        t = i / RATE
        tone = math.sin(math.tau * 1700 * t) + 0.5 * noise.uniform(-1, 1)
        out.append(tone * math.exp(-t / 0.008))
    return out


KICK, CLOSED, OPEN, CLAP = kick(), hat(0.02, 0.1), hat(0.11, 0.5), clap()
RISER, IMPACT, TICK = riser(), impact(), tick()


# --- Timbre de un polígono: un punto recorre sus aristas --------------------------------


def shape_table(sides: int, edges: tuple[int, ...]) -> list[float]:
    """Un ciclo de onda: la `x` de un punto que recorre las aristas que quedan a rapidez
    constante. Con huecos, el punto salta y el sonido se vuelve más brillante."""
    xs: list[float] = []
    per = TABLE / len(edges)
    for i, k in enumerate(edges):
        a, b = polygon_edge(1.0, sides, k)
        s, e = round(i * per), round((i + 1) * per)
        xs.extend(a.lerp(b, (j - s) / (e - s)).x for j in range(s, e))
    mean = sum(xs) / len(xs)
    peak = max(abs(v - mean) for v in xs) or 1.0
    return [(v - mean) / peak for v in xs]


_cache: dict = {}


def poly_note(sides: int, edges: tuple[int, ...], freq: float) -> list[float]:
    """Nota de un loop de enemigo: el polígono que le queda es el timbre."""
    key = ("poly", sides, edges, round(freq, 2))
    if key not in _cache:
        table = shape_table(sides, edges)
        inc = freq * TABLE / RATE
        out, ph = [], 0.0
        for i in range(int(0.22 * RATE)):
            env = min(1.0, i / 60) * math.exp(-i / RATE / 0.07)
            out.append(table[int(ph) % TABLE] * env)
            ph += inc
        _cache[key] = lowpass(out, 5000)
    return _cache[key]


def blip(freq: float) -> list[float]:
    """El arma punto: un pluck de diente de sierra, corto."""
    key = ("blip", round(freq, 2))
    if key not in _cache:
        out, ph = [], 0.0
        for i in range(int(0.15 * RATE)):
            ph = (ph + freq / RATE) % 1.0
            out.append((2 * ph - 1) * math.exp(-i / RATE / 0.04))
        _cache[key] = lowpass(out, 2500)
    return _cache[key]


def stab(chord: tuple[int, ...]) -> list[float]:
    """Acorde corto de house: el remate de una muerte y de la capa 3."""
    key = ("stab", chord)
    if key not in _cache:
        n = int(0.3 * RATE)
        out = [0.0] * n
        for semis in chord:
            f = hz(semis + 12, A3)
            ph = 0.0
            for i in range(n):
                ph = (ph + f / RATE) % 1.0
                out[i] += (2 * ph - 1) * math.exp(-i / RATE / 0.09) / len(chord)
        _cache[key] = lowpass(lowpass(out, 2200), 2200)
    return _cache[key]


# --- La partida ---------------------------------------------------------------------------


def play(seconds: float, seed: int):
    """Juega con el piloto de la demo. Devuelve los eventos `(segundo, tipo, datos)` y,
    por paso, `(intensidad cruda, enemigos cercanos, cooldown del arma, enemigos)`."""
    events = []
    frames = []
    games = 0
    world = World(BALANCE, random.Random(seed), lethal=not IMMORTAL)
    clock = 0.0
    for _ in range(round(seconds / STEP)):
        if world.game_over:
            games += 1
            next_game = next_seed(seed, games, demo=True, fixed=True)
            world = World(BALANCE, random.Random(next_game))
            events.append((clock, "game_over", ()))
        before = [(e, tuple(e.edges)) for e in world.enemies]
        old_bullets = {id(b) for w in world.weapons for b in w.bullets}
        held = [b for w in world.weapons for b in w.bullets]  # que no se reusen los id
        world.update(pilot_intent(world.steps))
        clock += STEP
        for enemy, edges in before:
            if len(enemy.edges) < len(edges):
                events.append((clock, "hit", ()))
            if not enemy.alive:
                events.append((clock, "death", ()))
        if any(id(b) not in old_bullets for w in world.weapons for b in w.bullets):
            events.append((clock, "shot", ()))
        del held
        p = world.player.position
        near = sorted(world.enemies, key=lambda e: e.position.distance_squared_to(p))
        loops = []
        for e in near[:MAX_LOOPS]:
            d = e.position - p
            angle = math.atan2(d.y, d.x)
            loops.append((id(e), angle, d.length(), e.spec.sides, tuple(e.edges)))
        raw = sum(
            len(e.edges) / e.spec.sides * math.exp(-e.position.distance_to(p) / 400)
            for e in world.enemies
        )
        cooldown = BALANCE.point_weapon.cooldown
        frames.append((raw, loops, cooldown, len(world.enemies)))
    return events, frames


# --- El secuenciador ----------------------------------------------------------------------


class Sequencer:
    """Recibe lo que pasó y entrega un bloque por semicorchea. No sabe de pygame."""

    def __init__(self) -> None:
        self.voices: list[tuple[int, list[float], float, str, float]] = []
        """(inicio, muestras, ganancia, bus, envío al delay). Bus: 'drums' o 'music'."""
        self.level = 0
        self.target = 0
        self.smooth = 0.0
        self.kick_age = 10**9
        self.pad_ph = [0.0] * 5
        self.bass_ph = 0.0
        self.svf_pad = [0.0, 0.0]
        self.svf_bass = [0.0, 0.0]
        self.bass_env = 0.0
        self.delay_len = 3 * round(S16)  # corchea con puntillo
        self.delay_l = [0.0] * self.delay_len
        self.delay_r = [0.0] * self.delay_len
        self.delay_pos = 0
        self.shot_pending = False
        self.lfo = 0.0

    def add(
        self,
        start: int,
        xs: list[float],
        gain: float,
        bus: str = "music",
        send: float = 0.0,
    ) -> None:
        self.voices.append((start, xs, gain, bus, send))

    def block(self, g: int, raw: float, loops, cooldown: float, events) -> array:
        """Mezcla la semicorchea `g`."""
        start, end = grid(g), grid(g + 1)
        size = end - start
        bar, s = divmod(g, 16)
        swung = start + (SWING if s % 2 else 0)

        # La intensidad sube en ~1 s y baja en ~5 s.
        target = 1 - math.exp(-raw / 3)
        tau = 1.0 if target > self.smooth else 5.0
        self.smooth += (target - self.smooth) * (S16 / RATE) / tau
        reset = any(k == "game_over" for k, _ in events)
        if reset:
            self.level, self.target, self.smooth = 0, 0, 0.0
            if BASE:
                self.add(start, IMPACT, 0.6, "drums")

        # Frases: se decide en el último compás y se cambia al empezar la siguiente.
        if s == 0 and bar % PHRASE == PHRASE - 1:
            want = sum(self.smooth > th for th in (0.08, 0.2, 0.38))
            self.target = want
            if want > self.level and BASE:
                self.add(start, RISER, 0.5, "drums")
        if s == 0 and bar % PHRASE == 0 and self.target != self.level:
            if self.target > self.level and BASE:
                self.add(start, IMPACT, 0.45, "drums")
            self.level = self.target
        lv = self.level
        last_bar = bar % PHRASE == PHRASE - 1
        rising = last_bar and self.target > lv

        root, voicing = chord_at(bar)

        # Base fija.
        if BASE and lv >= 1 and s % 4 == 0 and not (rising and s == 12):
            self.add(start, KICK, 0.95, "drums")
            self.kick_age = 0
        if BASE and lv >= 1 and s % 4 == 2:
            self.add(swung, CLOSED, 0.22, "drums")
        if BASE and lv >= 2 and s in (4, 12):
            self.add(start, CLAP, 0.5, "drums", 0.15)
        if BASE and lv >= 3 and s % 2 == 1:
            self.add(swung, CLOSED, 0.1, "drums")
        if BASE and lv >= 3 and s % 4 == 2:
            self.add(swung, OPEN, 0.12, "drums")
        if BASE and lv >= 3 and s in (3, 10):
            self.add(swung, stab(voicing), 0.35, "music", 0.3)
        bass_on = BASE and lv >= 2 and (s % 4 == 2 or (lv >= 3 and s == 15))

        # El arma punto: E(k, 16) con k según su cooldown; suena solo si disparó.
        if any(k == "shot" for k, _ in events):
            self.shot_pending = True
        k = max(1, min(16, round(BAR / cooldown)))
        slots = euclid(k, 16)
        if GAME and slots[s] and self.shot_pending:
            note = voicing[(s // 2) % 2 * 2 + 1]  # alterna las notas 1 y 3 del voicing
            self.add(swung, blip(hz(note + 24, A3 / 2)), 0.22, "music", 0.45)
            self.shot_pending = False

        # Los enemigos: E(lados, 16), rotado por su ángulo; golpe i ↔ arista i.
        for rank, (_, angle, dist, sides, edges) in enumerate(loops if GAME else []):
            rot = round((angle % math.tau) / math.tau * 16)
            pattern = euclid(sides, 16)
            step = (s - rot) % 16
            if not pattern[step]:
                continue
            i = sum(pattern[:step])  # qué golpe del loop es
            if i not in edges:
                continue  # esa arista ya no está: ese golpe se perdió
            note = voicing[i % len(voicing)] + 12 * (rank == 0)
            gain = 0.30 * math.exp(-dist / 450)
            note_xs = poly_note(sides, edges, hz(note, A3))
            self.add(swung, note_xs, gain, "music", 0.35)

        for kind, _ in events if GAME else []:
            if kind == "hit":
                self.add(swung, TICK, 0.25, "drums", 0.2)
            elif kind == "death":
                self.add(start, stab(voicing), 0.45, "music", 0.4)

        # Las voces de un disparo: la música va a un bus que el sidechain agacha.
        left = [0.0] * size
        right = [0.0] * size
        send = [0.0] * size
        music = [0.0] * size
        for vstart, xs, gain, bus, snd in self.voices:
            lo, hi = max(start, vstart), min(end, vstart + len(xs))
            for j in range(lo, hi):
                v = xs[j - vstart] * gain
                send[j - start] += v * snd
                if bus == "drums":
                    left[j - start] += v
                    right[j - start] += v
                else:
                    music[j - start] += v
        self.voices = [v for v in self.voices if v[0] + len(v[1]) > end]

        # Síntesis continua: pad y bajo con filtro resonante, sidechain y delay.
        cutoff = 250 * 2 ** (self.smooth * 4.2)
        detune = (0.996, 1.004, 1.0, 0.997, 1.003)
        pad_incs = [hz(n, A3) / RATE * d for n, d in zip(voicing, detune, strict=True)]
        bass_f = hz(root, A1) / RATE
        lp_p, bp_p = self.svf_pad
        lp_b, bp_b = self.svf_bass
        q_pad, q_bass = 0.7, 0.35  # menor q, más resonancia
        dl, dr, pos, dlen = self.delay_l, self.delay_r, self.delay_pos, self.delay_len
        ph = self.pad_ph
        bph, benv, age = self.bass_ph, self.bass_env, self.kick_age
        lfo = self.lfo
        pad_gain = (0.10 if lv == 0 else 0.07) if BASE else 0.0
        ducking = BASE and lv >= 1
        for i in range(size):
            lfo += 0.25 / RATE
            fc = min(5500.0, cutoff * (1 + 0.25 * math.sin(math.tau * lfo)))
            f = 2 * math.sin(math.pi * fc / RATE)
            saw = 0.0
            for v in range(5):
                ph[v] = (ph[v] + pad_incs[v]) % 1.0
                saw += 2 * ph[v] - 1
            hp = saw - lp_p - q_pad * bp_p
            bp_p += f * hp
            lp_p += f * bp_p
            if bass_on and i == 0:
                benv = 1.0
            benv *= 0.99988
            bph = (bph + bass_f) % 1.0
            fc_bass = min(1800.0, 120 + cutoff * 0.4 + 900 * benv)
            fb = 2 * math.sin(math.pi * fc_bass / RATE)
            x = (2 * bph - 1) * benv
            hpb = x - lp_b - q_bass * bp_b
            bp_b += fb * hpb
            lp_b += fb * bp_b
            # Sidechain: después de cada bombo, todo lo que no es batería baja un 70 %
            # y vuelve en 200 ms.
            duck = 1.0
            if ducking:
                duck -= 0.7 * max(0.0, 1.0 - age / (0.2 * RATE)) ** 2
            age += 1
            m = (lp_p * pad_gain + lp_b * 0.42 + music[i]) * duck
            # Delay ping-pong de corchea con puntillo.
            out_l, out_r = dl[pos], dr[pos]
            dl[pos] = send[i] + out_r * 0.38
            dr[pos] = out_l * 0.38
            pos = (pos + 1) % dlen
            left[i] = math.tanh(left[i] + m + out_l * 0.5 * duck)
            right[i] = math.tanh(right[i] + m + out_r * 0.5 * duck)
        self.svf_pad = [lp_p, bp_p]
        self.svf_bass = [lp_b, bp_b]
        self.delay_pos, self.lfo = pos, lfo
        self.bass_ph, self.bass_env, self.kick_age = bph, benv, age

        out = array("h", bytes(4 * size))
        for i in range(size):
            out[2 * i] = int(left[i] * 29000)
            out[2 * i + 1] = int(right[i] * 29000)
        return out


def main() -> None:
    path = sys.argv[1]
    seconds = float(sys.argv[2]) if len(sys.argv) > 2 else 90.0
    seed = int(sys.argv[3]) if len(sys.argv) > 3 else 1
    events, frames = play(seconds, seed)
    per_block: dict[int, list] = {}
    for t, kind, data in events:
        g = math.ceil((t * RATE + LOOKAHEAD) / S16)
        if kind == "death":
            g += g % 2  # a la corchea
        per_block.setdefault(g, []).append((kind, data))

    seq = Sequencer()
    out = array("h")
    costs, timeline = [], []
    for g in range(int(seconds * RATE / S16)):
        t = grid(g) / RATE
        raw, loops, cooldown, count = frames[min(len(frames) - 1, int(t / STEP))]
        t0 = time.perf_counter()
        out.extend(seq.block(g, raw, loops, cooldown, per_block.get(g, [])))
        costs.append((time.perf_counter() - t0) * 1000)
        if g % (16 * PHRASE) == 0:
            timeline.append(f"{seq.level}/{seq.smooth:.2f}/{count}")

    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(out.tobytes())
    cs = sorted(costs)
    block_ms = S16 / RATE * 1000
    print(
        f"Mezcla por bloque ({block_ms:.0f} ms de audio): "
        f"media {statistics.mean(costs):.1f} ms, "
        f"p99 {cs[int(len(cs) * 0.99)]:.1f} ms, máx {max(costs):.1f} ms"
    )
    print("Por frase (4 compases): capa / intensidad / enemigos")
    print("  " + "  ".join(timeline))
    print("sha256:", hashlib.sha256(out.tobytes()).hexdigest()[:16], " WAV:", path)


if __name__ == "__main__":
    main()
