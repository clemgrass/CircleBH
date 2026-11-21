"""El secuenciador: avanza con los pasos de la escena y entrega bloques de audio (ADR 0022).

La música avanza por semicorcheas. Cuando la escena llega al paso en que empieza la
semicorchea `g`, el secuenciador decide qué suena en ella con lo que pasó **antes** de
ese paso, y la mezcla de a trozos en los pasos siguientes. Al empezar la siguiente, el
bloque `g` queda en `ready`. Así, el audio depende solo de la secuencia de pasos: con la
misma semilla, los mismos bytes.

La mezcla tiene dos buses: la batería va directo, y la música (pad, bajo y notas) pasa
por el sidechain, que la agacha después de cada bombo. Las dos capas tienen su volumen:
`base_volume` para la base y `game_volume` para lo que sale del juego.
"""

import math
from array import array
from collections import deque
from dataclasses import dataclass

from circlebh.audio import sounds
from circlebh.audio.harmony import (
    A1,
    A3,
    Chord,
    Variation,
    chord_at,
    hz,
    variation_for,
)
from circlebh.audio.intensity import (
    FREE,
    PHRASE,
    PHRASE_BARS,
    Arrangement,
    Cue,
    Layers,
    raw_intensity,
)
from circlebh.audio.rhythm import RATE, SIXTEENTHS, Grid
from circlebh.audio.voices import (
    EnemyView,
    Note,
    enemy_notes,
    nearest_views,
    voice_for,
    weapon_note,
)
from circlebh.balance import BALANCE
from circlebh.world.clock import STEP
from circlebh.world.events import Death, Event, Hit, Shot
from circlebh.world.game import World
from circlebh.world.weapons import Weapon

SAMPLES_PER_STEP = round(RATE * STEP)
"""Muestras que dura un paso: 735. Es lo que se mezcla en cada paso."""
HISTORY = 4096
"""Cuántas decisiones se guardan: unos 8 minutos a 124 BPM."""
PEAK = 29000
"""El valor de 16 bits que corresponde a 1 después de la saturación."""
DETUNE = (0.996, 1.004, 1.0, 0.997, 1.003)
"""El desafinado de cada voz del pad: lo que lo hace sonar ancho."""
DUCK_DEPTH = 0.7
DUCK_SECONDS = 0.2
"""El sidechain baja la música un 70 % con cada bombo, y vuelve en 200 ms."""
DELAY_FEEDBACK = 0.38
PAD_Q, BASS_Q = 0.7, 0.35
ROLL_EVERY = (4, 2, 1, 1)
"""Cada cuántas semicorcheas suena el clap del redoble, en cada compás de la subida."""
"""Amortiguación de los filtros resonantes: menos, más resonancia."""


@dataclass(frozen=True)
class Decision:
    """Lo que el secuenciador decidió para la semicorchea `g`."""

    g: int
    level: int
    cues: tuple[Cue, ...]
    variation: Variation
    chord: Chord
    notes: tuple[Note, ...]
    """Las notas de los loops de enemigos."""
    weapon_hits: int
    """Cuántas armas sonaron en su loop."""
    rims: int
    """Cuántos golpes de bala sonaron."""
    death: bool
    silent: bool
    """Si la base calló: el último pulso de una subida (ADR 0026)."""


@dataclass(frozen=True)
class _Voice:
    """Un sonido de un disparo, puesto en la línea de tiempo."""

    start: int
    """En muestras desde que partió la música."""
    samples: sounds.Samples
    gain: float
    ducked: bool
    """Si pasa por el sidechain (la música) o va directo (la batería)."""
    send: float
    """Cuánto va al delay."""

    @property
    def end(self) -> int:
        return self.start + len(self.samples)


@dataclass(frozen=True)
class _Snapshot:
    """Lo que importa del mundo, al final de un paso."""

    raw: float
    views: tuple[EnemyView, ...]
    weapons: tuple[Weapon, ...]


CALM = _Snapshot(0.0, (), ())


@dataclass
class _Block:
    """La semicorchea que se está mezclando, con lo que la síntesis continua necesita."""

    start: int
    size: int
    level: int
    muted: bool
    """Si el pad y el bajo callan en este bloque."""
    cutoff: float
    pad_steps: list[float]
    bass_step: float
    bass_on: bool
    out: array[int]
    pos: int = 0


class Sequencer:
    """La música de una sesión. Avanza con `step(world)`, una vez por paso de la escena,
    y deja los bloques terminados en `ready`, como bytes estéreo de 16 bits."""

    def __init__(
        self, seed: int, *, base_volume: float = 1.0, game_volume: float = 1.0
    ) -> None:
        self.grid = Grid(BALANCE.director.bpm)
        """La grilla del tempo del tema, el mismo del director (ADR 0025). No cambia al
        reiniciar."""
        self.ready: deque[bytes] = deque()
        self.decisions: deque[Decision] = deque(maxlen=HISTORY)
        self.base_volume = base_volume
        self.game_volume = game_volume
        self._variation = variation_for(seed)
        self._next_variation: Variation | None = None
        self._first_bar = 0
        """El compás en que partió la progresión de la variación actual."""
        self._bar_cues: list[Cue] = []
        """Lo que espera a la variación nueva para sonar con ella: el impacto del
        reinicio."""
        self._arrangement = Arrangement()
        self._world: World | None = None
        self._world_steps = -1
        """Los pasos que llevaba `_world` cuando se leyeron sus eventos."""
        self._was_over = False
        self._steps = 0
        self._g = -1
        """La última semicorchea decidida."""
        self._pending: list[Event] = []
        self._cues: list[Cue] = []
        self._armed: set[int] = set()
        """Las armas (por `id`) que dispararon desde su último golpe de loop."""
        self._snapshot = CALM
        self._voices: list[_Voice] = []
        self._block: _Block | None = None
        # Estado de la síntesis continua: pad, bajo, sidechain y delay.
        self._pad_phases = [0.0] * len(DETUNE)
        self._pad_filter = [0.0, 0.0]
        self._bass_phase = 0.0
        self._bass_filter = [0.0, 0.0]
        self._bass_env = 0.0
        self._kick_at = -(10**9)
        self._lfo = 0.0
        self._delay_l = [0.0] * (3 * round(self.grid.samples))  # corchea con puntillo
        self._delay_r = [0.0] * len(self._delay_l)
        self._delay_pos = 0
        self._warm_up()

    def _warm_up(self) -> None:
        """Genera la batería ahora: la primera vez, un sonido cuesta hasta 70 ms, y a
        mitad de partida se notaría como un tirón. Las notas, que dependen de la forma de
        cada enemigo, se generan al sonar por primera vez."""
        sounds.kick()
        sounds.closed_hat()
        sounds.open_hat()
        sounds.clap()
        sounds.impact()
        sounds.rim()
        sounds.riser(self.grid.bar_seconds)
        # La subida de una frase: cuesta unos 250 ms, mejor ahora que antes del drop.
        sounds.riser(PHRASE_BARS * self.grid.bar_seconds)

    def start_game(self, seed: int) -> None:
        """Una partida nueva: su tonalidad entra en el compás siguiente, con su acorde
        inicial completo (sus dos compases) y con el impacto del reinicio, como una
        transición de DJ. El tempo no cambia."""
        self._next_variation = variation_for(seed)

    def step(self, world: World) -> None:
        """Avanza un paso de la escena, con `world` como quedó después de su `update`."""
        if world is not self._world:
            if self._world is not None:
                # Si viene una tonalidad nueva, el impacto espera para caer con ella.
                cues = self._reset_arrangement()
                if self._next_variation is not None:
                    self._bar_cues += cues
                else:
                    self._cues += cues
            self._world = world
            self._world_steps = -1
            self._was_over = False
            # Lo pendiente era de la partida anterior: no suena en la nueva.
            self._pending = []
            self._armed.clear()
        if world.game_over and not self._was_over:
            self._cues += self._reset_arrangement()
            self._was_over = True

        now = self._steps * SAMPLES_PER_STEP
        while self.grid.start(self._g + 1) <= now:
            self._g += 1
            if self._block is not None:
                self._finish_block()
            self._decide(self._g)
        self._mix(SAMPLES_PER_STEP)

        # Los eventos de un paso del mundo se leen una sola vez: con la partida perdida,
        # la escena ya no llama a `update` y `world.events` se queda con los del paso
        # fatal, pero el secuenciador sigue avanzando.
        if world.steps != self._world_steps:
            self._pending += world.events
            self._world_steps = world.steps
        self._snapshot = _snapshot(world)
        self._steps += 1

    # --- Decidir una semicorchea ---

    def _decide(self, g: int) -> None:
        bar, s = divmod(g, SIXTEENTHS)
        if s == 0 and self._next_variation is not None:
            # La progresión parte de nuevo en este compás: el acorde inicial suena
            # completo, y el impacto que esperaba cae aquí.
            self._variation, self._next_variation = self._next_variation, None
            self._first_bar = bar
            self._cues += self._bar_cues
            self._bar_cues = []
        start = self.grid.start(g)
        swung = start + self.grid.swing(g)
        # Las frases y las secciones se cuentan desde el compás en que entró la partida
        # (ADR 0026): con R1, es el mismo en que la partida dio su primer paso.
        game_g = g - self._first_bar * SIXTEENTHS
        cues = self._cues + self._arrangement.advance(
            self._snapshot.raw, game_g, self.grid.samples / RATE, self._layers_at
        )
        self._cues = []
        level = self._arrangement.level
        chord = chord_at(bar - self._first_bar, self._variation)
        root, voicing = chord
        silent = self._arrangement.silent(game_g)

        if not silent:
            self._add_base(game_g, start, swung, level, cues, voicing)
        weapon_hits = self._add_weapons(s, swung, voicing)
        notes = tuple(enemy_notes(self._snapshot.views, s, voicing))
        for note in notes:
            sample = sounds.poly_note(note.sides, note.edges, hz(note.semitones, A3))
            self._add(swung, sample, note.gain, game=True, send=0.35)
        rims, death = self._add_accents(g, start, swung, voicing)

        bass_on = (
            not silent
            and level >= 2
            and (s % 4 == 2 or (level >= 3 and s == SIXTEENTHS - 1))
        )
        self._open_block(start, level, voicing, root, bass_on, muted=silent)
        self.decisions.append(
            Decision(
                g,
                level,
                tuple(cues),
                self._variation,
                chord,
                notes,
                weapon_hits,
                rims,
                death,
                silent,
            )
        )

    def _reset_arrangement(self) -> list[Cue]:
        """Vuelve a la calma con un impacto, y corta el riser de una subida en curso: no
        puede seguir subiendo hacia un drop que ya no llega."""
        build = sounds.riser(PHRASE_BARS * self.grid.bar_seconds)
        self._voices = [v for v in self._voices if v.samples is not build]
        return self._arrangement.reset()

    def _layers_at(self, bar: int) -> Layers:
        """Las capas que permite la sección del compás `bar` de la partida. Con la
        partida perdida, o sin partida, manda la intensidad."""
        world = self._world
        if world is None or world.game_over:
            return FREE
        return world.director.section_at(bar).layers

    @property
    def waiting_for_bar(self) -> bool:
        """Si hay una partida nueva esperando su compás (R1, ADR 0026). Mientras tanto,
        la escena no avanza el mundo: así la partida, la tonalidad y el impacto parten
        en el mismo golpe."""
        return self._next_variation is not None

    def _add(
        self,
        start: int,
        samples: sounds.Samples,
        gain: float,
        *,
        game: bool,
        ducked: bool = True,
        send: float = 0.0,
    ) -> None:
        volume = self.game_volume if game else self.base_volume
        self._voices.append(_Voice(start, samples, gain * volume, ducked, send))

    def _add_base(
        self,
        g: int,
        start: int,
        swung: int,
        level: int,
        cues: list[Cue],
        voicing: tuple[int, ...],
    ) -> None:
        """La batería y los acordes de la base, según la capa."""
        s = g % SIXTEENTHS
        drums = {"game": False, "ducked": False}
        if "riser" in cues:
            self._add(start, sounds.riser(self.grid.bar_seconds), 0.5, **drums)
        if "build" in cues:
            seconds = PHRASE_BARS * self.grid.bar_seconds
            self._add(start, sounds.riser(seconds), 0.55, **drums)
        if self._arrangement.building(g):
            self._add_roll(g, start)
        if "impact" in cues:
            self._add(start, sounds.impact(), 0.5, **drums)
        # Antes de subir, el bombo calla en el último pulso del compás.
        if level >= 1 and s % 4 == 0 and not (self._arrangement.rising(g) and s == 12):
            self._add(start, sounds.kick(), 0.95, **drums)
            self._kick_at = start
        if level >= 1 and s % 4 == 2:
            self._add(swung, sounds.closed_hat(), 0.22, **drums)
        if level >= 2 and s in (4, 12):
            self._add(start, sounds.clap(), 0.5, **drums, send=0.15)
        if level >= 3 and s % 2 == 1:
            self._add(swung, sounds.closed_hat(), 0.1, **drums)
        if level >= 3 and s % 4 == 2:
            self._add(swung, sounds.open_hat(), 0.12, **drums)
        if level >= 3 and s in (3, 10):
            self._add(swung, sounds.stab(voicing), 0.35, game=False, send=0.3)

    def _add_roll(self, g: int, start: int) -> None:
        """El redoble de la subida: un clap por pulso en su primer compás, por corchea
        en el segundo y por semicorchea en los dos últimos, cada vez más fuerte."""
        k = g % PHRASE
        every = ROLL_EVERY[k // SIXTEENTHS]
        if k % every == 0:
            gain = 0.15 + 0.30 * k / PHRASE
            self._add(start, sounds.clap(), gain, game=False, ducked=False)

    def _add_weapons(self, s: int, swung: int, voicing: tuple[int, ...]) -> int:
        """Cada arma suena en su loop, solo si disparó desde su golpe anterior."""
        self._armed |= {id(e.weapon) for e in self._pending if isinstance(e, Shot)}
        hits = 0
        for weapon in self._snapshot.weapons:
            pattern = voice_for(weapon).pattern(weapon, self.grid.bar_seconds)
            if pattern[s] and id(weapon) in self._armed:
                note = sounds.blip(hz(weapon_note(s, voicing), A3))
                self._add(swung, note, 0.22, game=True, send=0.45)
                self._armed.discard(id(weapon))
                hits += 1
        return hits

    def _add_accents(
        self, g: int, start: int, swung: int, voicing: tuple[int, ...]
    ) -> tuple[int, bool]:
        """Un rim por cada golpe de bala, y un acorde corto si murió alguien.

        Una muerte cae en la corchea: en una semicorchea impar, espera a la siguiente.
        """
        rims = sum(isinstance(e, Hit) for e in self._pending)
        for _ in range(rims):
            self._add(swung, sounds.rim(), 0.25, game=True, ducked=False, send=0.2)
        deaths = [e for e in self._pending if isinstance(e, Death)]
        death = bool(deaths) and g % 2 == 0
        if death:
            self._add(start, sounds.stab(voicing), 0.45, game=True, send=0.4)
        self._pending = [*deaths] if deaths and not death else []
        return rims, death

    def _open_block(
        self,
        start: int,
        level: int,
        voicing: tuple[int, ...],
        root: int,
        bass_on: bool,
        *,
        muted: bool,
    ) -> None:
        self._block = _Block(
            start=start,
            size=self.grid.start(self._g + 1) - start,
            level=level,
            muted=muted,
            cutoff=250 * 2 ** (self._arrangement.brightness * 4.2),
            pad_steps=[
                hz(n, A3) / RATE * d for n, d in zip(voicing, DETUNE, strict=True)
            ],
            bass_step=hz(root, A1) / RATE,
            bass_on=bass_on,
            out=array("h"),
        )

    # --- Mezclar ---

    def _finish_block(self) -> None:
        block = self._block
        assert block is not None
        self._mix(block.size - block.pos)
        self.ready.append(block.out.tobytes())
        end = block.start + block.size
        self._voices = [v for v in self._voices if v.end > end]

    def _mix(self, n: int) -> None:
        """Mezcla hasta `n` muestras más del bloque en curso."""
        block = self._block
        if block is None:
            return
        a, b = block.pos, min(block.pos + n, block.size)
        if a >= b:
            return
        size = b - a
        offset = block.start + a
        drums = [0.0] * size
        music = [0.0] * size
        send = [0.0] * size
        for voice in self._voices:
            lo, hi = max(offset, voice.start), min(offset + size, voice.end)
            bus = music if voice.ducked else drums
            for j in range(lo, hi):
                x = voice.samples[j - voice.start] * voice.gain
                bus[j - offset] += x
                send[j - offset] += x * voice.send
        self._synthesize(block, a, drums, music, send)
        block.pos = b

    def _synthesize(
        self,
        block: _Block,
        a: int,
        drums: list[float],
        music: list[float],
        send: list[float],
    ) -> None:
        """El pad y el bajo muestra a muestra, con sus filtros resonantes, el sidechain y
        el delay ping-pong. Escribe el resultado saturado en `block.out`."""
        tanh, sin, tau, pi = math.tanh, math.sin, math.tau, math.pi
        level, cutoff = block.level, block.cutoff
        # En el silencio de la subida, el pad y el bajo siguen oscilando, pero callan.
        on = 0.0 if block.muted else self.base_volume
        pad_gain = (0.10 if level == 0 else 0.07) * on
        bass_gain = 0.42 * on
        ducking = level >= 1 and self.base_volume > 0
        duck_samples = DUCK_SECONDS * RATE
        phases, pad_steps = self._pad_phases, block.pad_steps
        voices = range(len(phases))
        lp_p, bp_p = self._pad_filter
        lp_b, bp_b = self._bass_filter
        bass_phase, bass_env, lfo = self._bass_phase, self._bass_env, self._lfo
        dl, dr, pos, dlen = (
            self._delay_l,
            self._delay_r,
            self._delay_pos,
            len(self._delay_l),
        )
        out = block.out
        sample = block.start + a
        for i in range(len(drums)):
            lfo += 0.25 / RATE
            fc = min(5500.0, cutoff * (1 + 0.25 * sin(tau * lfo)))
            f = 2 * sin(pi * fc / RATE)
            saw = 0.0
            for v in voices:
                phases[v] = (phases[v] + pad_steps[v]) % 1.0
                saw += 2 * phases[v] - 1
            bp_p += f * (saw - lp_p - PAD_Q * bp_p)
            lp_p += f * bp_p
            if block.bass_on and a + i == 0:
                bass_env = 1.0
            bass_env *= 0.99988
            bass_phase = (bass_phase + block.bass_step) % 1.0
            fb = 2 * sin(pi * min(1800.0, 120 + cutoff * 0.4 + 900 * bass_env) / RATE)
            bp_b += fb * ((2 * bass_phase - 1) * bass_env - lp_b - BASS_Q * bp_b)
            lp_b += fb * bp_b
            duck = 1.0
            if ducking:
                duck -= (
                    DUCK_DEPTH
                    * max(0.0, 1.0 - (sample - self._kick_at) / duck_samples) ** 2
                )
            m = (lp_p * pad_gain + lp_b * bass_gain + music[i]) * duck
            out_l, out_r = dl[pos], dr[pos]
            dl[pos] = send[i] + out_r * DELAY_FEEDBACK
            dr[pos] = out_l * DELAY_FEEDBACK
            pos = (pos + 1) % dlen
            out.append(int(tanh(drums[i] + m + out_l * 0.5 * duck) * PEAK))
            out.append(int(tanh(drums[i] + m + out_r * 0.5 * duck) * PEAK))
            sample += 1
        self._pad_filter = [lp_p, bp_p]
        self._bass_filter = [lp_b, bp_b]
        self._bass_phase, self._bass_env, self._lfo = bass_phase, bass_env, lfo
        self._delay_pos = pos


def _snapshot(world: World) -> _Snapshot:
    """Lo que la música lee del mundo. Con la partida perdida, la calma: sin loops ni
    intensidad, mientras se ve la muerte."""
    if world.game_over:
        return CALM
    player = world.player.position
    return _Snapshot(
        raw_intensity(world.enemies, player),
        tuple(nearest_views(world.enemies, player)),
        tuple(world.weapons),
    )
