"""La línea base del balance (#90): qué pasa hoy en una partida, medido sin ventana.

Prototipo de la investigación `docs/investigaciones/2026-11-24-balance.md`. No es una
herramienta del juego: de aquí salen los números del informe, y las herramientas
definitivas las decide el ADR de balance.

Tres mediciones, todas con el balance real y el piloto de la demo (`pilot_intent`):

- **mortal:** una partida por semilla, hasta morir o hasta `--minutos`. Cuánto vive el
  piloto, en qué sección muere y qué lo rodeaba.
- **inmortal:** lo mismo con `lethal=False`, para ver la partida entera aunque el piloto
  no esquive. Por sección: la amenaza y las líneas que entran, las líneas que quita el
  arma, los vivos y el tiempo para matar a cada tipo.
- **cerco:** el escenario `octagono-cerco` (10 octágonos alrededor del piloto, sin
  director), 120 s. Cuántos mueren y cómo se reparte el daño.

Uso: `uv run python docs/prototipos/medir_balance.py --semillas 20 --minutos 8`.
"""

import argparse
import random
import statistics
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field, replace

from pygame.math import Vector2

from circlebh.balance import BALANCE
from circlebh.pilot import pilot_intent
from circlebh.world.clock import STEP
from circlebh.world.director import bar_at, start_from
from circlebh.world.enemy import Enemy
from circlebh.world.events import Death, Hit, Regrow, Shot
from circlebh.world.game import World
from circlebh.world.swarm import lattice

NAMES = {id(spec): name for name, spec in BALANCE.enemies.items()}
BPM = BALANCE.director.bpm


def name_of(enemy: Enemy) -> str:
    """El nombre del tipo. Una línea suelta nace con su `spec` cambiado (otro radio),
    así que, si no es el objeto del balance, se busca por la figura."""
    if id(enemy.spec) in NAMES:
        return NAMES[id(enemy.spec)]
    for name, spec in BALANCE.enemies.items():
        if spec.shape == enemy.spec.shape and spec.threat == enemy.spec.threat:
            return name
    return "?"


def section_key(world: World) -> str:
    """La sección en curso. El infinito se parte en bloques de una duplicación."""
    section = world.director.section
    if section.kind != "endless":
        return section.name
    doubling = BALANCE.director.endless.doubling
    block = int(bar_at(world.endless_steps, BPM) // doubling * doubling)
    return f"{section.name} +{block}"


@dataclass
class SectionStats:
    """Lo que pasó en una sección de una partida."""

    seconds: float = 0.0
    threat_in: float = 0.0
    lines_in: int = 0
    lines_out: int = 0
    regrown: int = 0
    shots: int = 0
    alive_samples: list[int] = field(default_factory=list)


@dataclass
class Run:
    """Una partida medida."""

    seed: int
    lethal: bool
    seconds: float = 0.0
    endless_seconds: float = 0.0
    section_at_end: str = ""
    nearest_at_death: str = ""
    sections: dict[str, SectionStats] = field(default_factory=dict)
    spawned: Counter[str] = field(default_factory=Counter)
    killed: Counter[str] = field(default_factory=Counter)
    ttk: dict[str, list[float]] = field(default_factory=lambda: defaultdict(list))
    danger_by_bar: list[tuple[float, float, float, float, int]] = field(
        default_factory=list
    )


def play(seed: int, lethal: bool, minutes: float, start: str = "") -> Run:
    """Juega una partida con el piloto y la mide paso a paso. `start` es la sección en
    que parte, como `debug.start_section`."""
    balance = replace(BALANCE, director=start_from(BALANCE.director, start))
    world = World(balance, random.Random(seed), lethal=lethal)
    run = Run(seed, lethal)
    # Guarda al enemigo mismo: si muriera y se liberara, Python podría darle su `id` a
    # uno nuevo.
    born: dict[int, tuple[int, str, Enemy]] = {}
    last_bar = -1
    for _ in range(round(minutes * 60 / STEP)):
        if world.game_over:
            break
        section = section_key(world)
        world.update(pilot_intent(world.steps))
        stats = run.sections.setdefault(section, SectionStats())
        stats.seconds += STEP
        for enemy in world.enemies:
            if id(enemy) not in born:
                name = name_of(enemy)
                born[id(enemy)] = (world.steps, name, enemy)
                run.spawned[name] += 1
                stats.threat_in += enemy.spec.threat
                stats.lines_in += len(enemy.edges)
        for event in world.events:
            match event:
                case Hit():
                    stats.lines_out += 1
                case Regrow():
                    stats.regrown += 1
                case Shot():
                    stats.shots += 1
                case Death(enemy=enemy) if id(enemy) in born:
                    step, name, _ = born[id(enemy)]
                    run.killed[name] += 1
                    run.ttk[name].append((world.steps - step) * STEP)
                case _:
                    pass
        bar = int(bar_at(world.steps, BPM))
        if bar != last_bar:
            last_bar = bar
            stats.alive_samples.append(len(world.enemies))
            if world.director.section.kind == "endless":
                d = world.director.danger
                run.danger_by_bar.append(
                    (bar, d.speed, d.cadence, d.sides, world.bodies)
                )
    run.seconds = world.elapsed
    run.endless_seconds = world.endless_steps * STEP
    run.section_at_end = world.director.section.name
    if world.game_over and world.enemies:
        p = world.player.position
        nearest = min(world.enemies, key=lambda e: e.position.distance_to(p))
        bullets = [b.position.distance_to(p) for b in world.enemy_bullets]
        near_bullet = min(bullets, default=1e9)
        body = nearest.position.distance_to(p) - nearest.radius
        run.nearest_at_death = "bala" if near_bullet < body else f"{name_of(nearest)}"
    return run


def siege(seconds: float = 120.0) -> tuple[int, list[int], int]:
    """El cerco: 10 octágonos a 90 del piloto, sin director. Devuelve los muertos, las
    líneas que perdió cada octágono, de más a menos, y los disparos."""
    quiet = replace(
        BALANCE,
        director=replace(
            BALANCE.director,
            sections=(replace(BALANCE.director.sections[0], deck=()),),
        ),
    )
    world = World(quiet, random.Random(1), lethal=False)
    octagon = quiet.enemies["octagon"]
    world.enemies = [Enemy(octagon, p) for p in lattice(Vector2(), 10, 90)]
    ring = list(world.enemies)
    lost = dict.fromkeys(map(id, ring), 0)
    dead = 0
    shots = 0
    for _ in range(round(seconds / STEP)):
        world.update(pilot_intent(world.steps))
        for event in world.events:
            shots += isinstance(event, Shot)
            if isinstance(event, Hit) and id(event.enemy) in lost:
                lost[id(event.enemy)] += 1
            if isinstance(event, Death) and id(event.enemy) in lost:
                dead += 1
    return dead, sorted(lost.values(), reverse=True), shots


def _play(args: tuple[int, bool, float] | tuple[int, bool, float, str]) -> Run:
    return play(*args)


def pct(values: list[float], q: float) -> float:
    if not values:
        return float("nan")
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, round(q * (len(ordered) - 1)))]


def report_mortal(runs: list[Run]) -> None:
    print("\n## Mortal: el piloto muere al primer toque\n")
    lives = [r.seconds for r in runs]
    print(
        f"Vida: mediana {statistics.median(lives):.1f} s, p10 {pct(lives, 0.1):.1f} s,"
        f" p90 {pct(lives, 0.9):.1f} s, máx {max(lives):.1f} s"
    )
    print("\n| Sección donde muere | Partidas |\n|---|---|")
    for name, count in Counter(r.section_at_end for r in runs).most_common():
        print(f"| {name} | {count} |")
    print("\n| Lo más cercano al morir | Partidas |\n|---|---|")
    for name, count in Counter(r.nearest_at_death for r in runs).most_common():
        print(f"| {name or '(nadie)'} | {count} |")


def report_immortal(runs: list[Run], title: str) -> None:
    print(f"\n## {title}\n")
    order = list(dict.fromkeys(name for r in runs for name in r.sections))
    print(
        "| Sección | s | amenaza/s | líneas que entran/s | líneas que quita el arma/s"
        " | puntería | curadas/s | vivos (mediana de los compases) |"
    )
    print("|---|---|---|---|---|---|---|---|")
    for name in order:
        rows = [r.sections[name] for r in runs if name in r.sections]
        if not rows:
            continue
        secs = statistics.median(s.seconds for s in rows)

        def rate(attr: str, rows: list[SectionStats] = rows) -> float:
            return statistics.median(getattr(s, attr) / s.seconds for s in rows)

        alive = statistics.median(
            statistics.median(s.alive_samples or [0]) for s in rows
        )
        aim = sum(s.lines_out for s in rows) / max(1, sum(s.shots for s in rows))
        print(
            f"| {name} | {secs:.0f} | {rate('threat_in'):.2f} | {rate('lines_in'):.2f}"
            f" | {rate('lines_out'):.2f} | {aim:.0%} | {rate('regrown'):.2f} | {alive:.0f} |"
        )
    print("\n| Tipo | aparecen | mueren | % muere | TTK mediana s | TTK p90 s |")
    print("|---|---|---|---|---|---|")
    spawned: Counter[str] = sum((r.spawned for r in runs), Counter())
    killed: Counter[str] = sum((r.killed for r in runs), Counter())
    for name, count in spawned.most_common():
        ttk = [t for r in runs for t in r.ttk.get(name, [])]
        share = 100 * killed[name] / count
        print(
            f"| {name} | {count} | {killed[name]} | {share:.0f} % |"
            f" {pct(ttk, 0.5):.1f} | {pct(ttk, 0.9):.1f} |"
        )
    endless = [r for r in runs if r.danger_by_bar]
    if endless:
        print(
            "\nInfinito, semilla",
            endless[0].seed,
            "(compás, velocidad, cadencia, lados, cuerpos):",
        )
        for row in endless[0].danger_by_bar[::4]:
            print("  ", row)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--semillas", type=int, default=20)
    parser.add_argument("--minutos", type=float, default=8.0)
    args = parser.parse_args()
    seeds = range(1, args.semillas + 1)
    with ProcessPoolExecutor() as pool:
        mortal = list(pool.map(_play, [(s, True, args.minutos) for s in seeds]))
        immortal = list(pool.map(_play, [(s, False, args.minutos) for s in seeds]))
        endless = list(
            pool.map(_play, [(s, False, args.minutos, "infinito") for s in seeds])
        )
    print(f"# Línea base: {args.semillas} semillas, hasta {args.minutos} min")
    report_mortal(mortal)
    report_immortal(immortal, "Inmortal: la partida entera, sin morir")
    report_immortal(endless, "Inmortal desde el infinito")
    dead, lost, shots = siege()
    print(
        f"\n## Cerco de octágonos, 120 s\n\nMueren {dead} de 10, con {shots} disparos y"
        f" {sum(lost)} líneas quitadas. Líneas perdidas por octágono: {lost}"
    )


if __name__ == "__main__":
    main()
