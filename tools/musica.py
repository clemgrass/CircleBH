"""Genera la música de la demo como WAV y mide cuánto cuesta mezclarla (ADR 0022).

Juega la demo sin ventana como la escena: el piloto, 2 s de muerte y la partida
siguiente con `next_seed`. Lleva el mismo `Sequencer` paso a paso y escribe
`.capturas/musica-seed<S>[-inmortal][-<solo>].wav`, para escuchar la evidencia sin
jugar.

Reporta los milisegundos por paso de `Sequencer.step` (la meta es 4 ms de media), la
capa de cada frase, la variación de cada partida y el sha256 del audio: con la misma
semilla, el mismo sha.

Uso: uv run poe musica [--segundos 120] [--semilla 1] [--inmortal] [--solo base|juego]
"""

import argparse
import hashlib
import random
import statistics
import time
import wave
from pathlib import Path

from circlebh.audio.harmony import variation_for
from circlebh.audio.intensity import PHRASE_BARS
from circlebh.audio.rhythm import RATE, SIXTEENTHS
from circlebh.audio.sequencer import Sequencer
from circlebh.balance import BALANCE
from circlebh.pilot import choose_at_random, pilot_intent
from circlebh.scenes.game import DEMO_RESTART_STEPS
from circlebh.seeds import next_seed
from circlebh.world.clock import STEP
from circlebh.world.game import World

OUT_DIR = Path(".capturas")
BUDGET_MS = 4.0
NOTES = ("La", "Si♭", "Si", "Do", "Do♯", "Re", "Mi♭", "Mi", "Fa", "Fa♯", "Sol", "La♭")


def parse() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--segundos", type=float, default=120.0)
    parser.add_argument("--semilla", type=int, default=1)
    parser.add_argument("--inmortal", action="store_true", help="el jugador no muere")
    parser.add_argument(
        "--solo", choices=("base", "juego"), help="genera solo esa capa"
    )
    return parser.parse_args()


def key_name(seed: int) -> str:
    variation = variation_for(seed)
    return f"{NOTES[variation.transpose % 12]} menor, parte en el acorde {variation.first_chord}"


def main() -> None:
    args = parse()
    sequencer = Sequencer(
        args.semilla,
        base_volume=0.0 if args.solo == "juego" else 1.0,
        game_volume=0.0 if args.solo == "base" else 1.0,
    )
    games = [args.semilla]
    world = World(BALANCE, random.Random(args.semilla), lethal=not args.inmortal)
    # Como la demo, elige cada mano al azar con una `Random` propia. La demo además la
    # muestra un rato, con la música detenida; aquí elige al tiro, y suena igual.
    chooser = random.Random(args.semilla)
    sequencer.start_game(args.semilla)
    dead_steps = 0
    costs = []
    for _ in range(round(args.segundos / STEP)):
        if not world.game_over:
            choose_at_random(world, chooser)
            world.update(pilot_intent(world.steps))
        else:
            dead_steps += 1
            if dead_steps >= DEMO_RESTART_STEPS:
                seed = next_seed(args.semilla, len(games), demo=True, fixed=True)
                games.append(seed)
                world = World(BALANCE, random.Random(seed))
                chooser = random.Random(seed)
                sequencer.start_game(seed)
                dead_steps = 0
        start = time.perf_counter()
        sequencer.step(world)
        costs.append((time.perf_counter() - start) * 1000)

    audio = b"".join(sequencer.ready)
    suffix = ("-inmortal" if args.inmortal else "") + (
        f"-{args.solo}" if args.solo else ""
    )
    path = OUT_DIR / f"musica-seed{args.semilla}{suffix}.wav"
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as out:
        out.setnchannels(2)
        out.setsampwidth(2)
        out.setframerate(RATE)
        out.writeframes(audio)

    costs.sort()
    mean = statistics.mean(costs)
    print(f"WAV: {path} ({len(audio) / 4 / RATE:.1f} s)")
    print(f"tempo: {sequencer.grid.bpm} BPM")
    for n, seed in enumerate(games):
        print(f"  partida {n} (semilla {seed}): {key_name(seed)}")
    print(
        f"mezcla por paso: media {mean:.2f} ms, p99 {costs[int(len(costs) * 0.99)]:.2f} ms, "
        f"máx {costs[-1]:.2f} ms (meta: {BUDGET_MS:.0f} ms de media)"
    )
    phrase = PHRASE_BARS * SIXTEENTHS
    layers = [str(d.level) for d in sequencer.decisions if d.g % phrase == 0]
    print("capa de cada frase:", " ".join(layers))
    print("sha256:", hashlib.sha256(audio).hexdigest()[:16])
    if mean > BUDGET_MS:
        print(f"OJO: la media pasa la meta de {BUDGET_MS:.0f} ms")


if __name__ == "__main__":
    main()
