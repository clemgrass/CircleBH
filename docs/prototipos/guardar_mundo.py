"""¿Se puede guardar una partida y retomarla? (#90, ronda 2)

Prototipo de la investigación `docs/investigaciones/2026-11-24-balance.md`, para la
decisión 6: medir el tema k partiendo del jugador como llegó, sin jugar los anteriores.

Juega una partida con el piloto de la demo hasta `CUT` pasos y la copia con
`copy.deepcopy` (en memoria) y con `pickle` (lo que iría a disco), que también copian su
`Random`. Después sigue las tres, la original y las dos copias, otros `AFTER` pasos con
la misma entrada, y compara su estado en cada paso. Si las copias son fieles, son
idénticas. También mide cuánto tarda cada copia y cuánto pesa.

Uso: `uv run python docs/prototipos/guardar_mundo.py`.
"""

import copy
import pickle
import random
import time

from circlebh.balance import BALANCE
from circlebh.pilot import pilot_intent
from circlebh.world.game import World

CUT = 9000
"""150 s: el drop 1 de una partida sin muerte, con unos 40 enemigos de varios tipos."""
AFTER = 3000
SEED = 3


def fingerprint(world: World) -> tuple[object, ...]:
    """Lo que tiene que calzar: el jugador, cada enemigo con sus líneas, las balas, la
    sección y el estado del azar."""
    return (
        tuple(world.player.position),
        world.game_over,
        world.director.section.name,
        tuple(
            (tuple(e.position), tuple(e.edges), e.angle, e.spec.threat)
            for e in world.enemies
        ),
        tuple(tuple(b.position) for b in world.enemy_bullets),
        world.rng.getstate(),
    )


def main() -> None:
    world = World(BALANCE, random.Random(SEED), lethal=False)
    for _ in range(CUT):
        world.update(pilot_intent(world.steps))
    start = time.perf_counter()
    in_memory = copy.deepcopy(world)
    copy_ms = (time.perf_counter() - start) * 1000
    start = time.perf_counter()
    data = pickle.dumps(world)
    # Cargar un pickle ejecuta código: aquí es seguro porque son bytes que escribió este
    # mismo proceso. Una herramienta nunca debe cargar uno que venga de afuera.
    on_disk = pickle.loads(data)
    pickle_ms = (time.perf_counter() - start) * 1000
    print(
        f"Paso {CUT}, {len(world.enemies)} enemigos: deepcopy {copy_ms:.1f} ms,"
        f" pickle {pickle_ms:.1f} ms y {len(data) / 1024:.0f} KiB"
    )
    for step in range(AFTER):
        for w in (world, in_memory, on_disk):
            w.update(pilot_intent(w.steps))
        if not fingerprint(world) == fingerprint(in_memory) == fingerprint(on_disk):
            print(f"Se separan {step + 1} pasos después de copiar.")
            return
    print(f"Las tres idénticas durante {AFTER} pasos más ({AFTER / 60:.0f} s).")


if __name__ == "__main__":
    main()
