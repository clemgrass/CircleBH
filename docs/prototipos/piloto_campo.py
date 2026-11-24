"""El piloto P1 (#90, ronda 2): esquiva con un campo de fuerzas, con ruido.

Prototipo de la investigación `docs/investigaciones/2026-11-24-balance.md`. Responde tres
preguntas antes del ADR de balance:

1. ¿Vive más que el piloto de la demo (P0), que da vueltas?
2. ¿Con menos ruido vive más? Si no, el ruido no sirve para simular la habilidad.
3. ¿Qué forma tiene hoy el riesgo por sección?

**Cómo juega.** Cada enemigo lo empuja con `1/d²`, donde `d` es la distancia entre su
borde y el círculo envolvente del enemigo, como las cargas del ADR 0021. Cada bala
enemiga empuja más fuerte, desde donde va a estar en `LOOKAHEAD` segundos. Si nada lo
empuja, da vueltas como P0. La habilidad es el ruido: la dirección se gira un ángulo
normal de desviación σ, que se sortea de nuevo cada `NOISE_STEPS` pasos (Isaksen y
Nealen, 2015). El ruido sale de su propia `Random`, nunca de la del mundo (ADR 0005).

**El riesgo por sección** es la tasa de muerte: las muertes en la sección divididas por
los segundos que pasaron en ella todas las partidas (una tasa de riesgo constante por
tramo, como en un análisis de supervivencia).

Uso: `uv run python docs/prototipos/piloto_campo.py --semillas 20 --minutos 8`.
"""

import argparse
import math
import random
from collections import Counter
from collections.abc import Callable
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field

from medir_balance import section_key
from pygame.math import Vector2

from circlebh.balance import BALANCE
from circlebh.pilot import pilot_intent
from circlebh.world.clock import STEP
from circlebh.world.game import World

REACH = 250.0
"""Más lejos que esto, un enemigo o una bala no lo empuja."""
NEAREST = 4.0
"""La distancia mínima en `1/d²`, para que la fuerza no se vaya al infinito."""
BULLET_WEIGHT = 4.0
"""Cuánto más empuja una bala que un enemigo."""
LOOKAHEAD = 0.3
"""Cuántos segundos adelante mira cada bala."""
NOISE_STEPS = 6
"""Cada cuántos pasos se sortea de nuevo el error: 0,1 s."""
SIGMAS = {"P0": None, "P1 σ=0,2": 0.2, "P1 σ=0,6": 0.6, "P1 σ=1,2": 1.2}
"""Los pilotos que se comparan. σ en radianes; `None` es el círculo de la demo."""


class FieldPilot:
    """P1: huye de lo que lo puede matar, con un error angular de desviación `sigma`."""

    def __init__(self, sigma: float, seed: int) -> None:
        self.sigma = sigma
        self.rng = random.Random(seed)
        self.error = 0.0

    def __call__(self, world: World) -> Vector2:
        here = world.player.position
        push = Vector2()
        for enemy in world.enemies:
            push += self._repel(here, enemy.position, enemy.radius, world, 1.0)
        for bullet in world.enemy_bullets:
            ahead = bullet.position + bullet.velocity * LOOKAHEAD
            push += self._repel(here, ahead, 0.0, world, BULLET_WEIGHT)
        if world.steps % NOISE_STEPS == 0:
            self.error = self.rng.gauss(0.0, self.sigma)
        if push.length_squared() == 0:
            return pilot_intent(world.steps)
        return push.normalize().rotate_rad(self.error)

    @staticmethod
    def _repel(
        here: Vector2, source: Vector2, radius: float, world: World, weight: float
    ) -> Vector2:
        offset = here - source
        gap = offset.length() - radius - world.player.radius
        if offset.length_squared() == 0 or gap > REACH:
            return Vector2()
        return offset.normalize() * weight / max(gap, NEAREST) ** 2


@dataclass
class Life:
    """Una partida: cuánto pasó en cada sección y dónde murió."""

    seconds: Counter[str] = field(default_factory=Counter)
    death: str = ""
    total: float = 0.0


def live(seed: int, sigma: float | None, minutes: float) -> Life:
    """Juega una partida mortal con el piloto dado, hasta morir o hasta `minutes`."""
    world = World(BALANCE, random.Random(seed))
    pilot: Callable[[World], Vector2] = (
        (lambda w: pilot_intent(w.steps)) if sigma is None else FieldPilot(sigma, seed)
    )
    life = Life()
    for _ in range(round(minutes * 60 / STEP)):
        section = section_key(world)
        world.update(pilot(world))
        life.seconds[section] += STEP
        if world.game_over:
            life.death = section
            break
    life.total = world.elapsed
    return life


def _live(args: tuple[int, float | None, float]) -> Life:
    return live(*args)


def report(name: str, lives: list[Life]) -> None:
    order = list(dict.fromkeys(s for life in lives for s in life.seconds))
    totals = sorted(life.total for life in lives)
    median = totals[len(totals) // 2]
    deaths = Counter(life.death for life in lives if life.death)
    print(f"\n### {name}\n")
    print(
        f"Vida mediana {median:.0f} s. Mueren {sum(deaths.values())} de {len(lives)}."
    )
    print("\n| Sección | llegan | mueren | s en total | riesgo (muertes/min) |")
    print("|---|---|---|---|---|")
    for section in order:
        reached = sum(1 for life in lives if section in life.seconds)
        exposure = sum(life.seconds[section] for life in lives)
        rate = 60 * deaths[section] / exposure if exposure else math.nan
        print(
            f"| {section} | {reached} | {deaths[section]} | {exposure:.0f} | {rate:.2f} |"
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--semillas", type=int, default=20)
    parser.add_argument("--minutos", type=float, default=8.0)
    args = parser.parse_args()
    seeds = range(1, args.semillas + 1)
    print(f"## Pilotos: {args.semillas} semillas, hasta {args.minutos} min, con muerte")
    with ProcessPoolExecutor() as pool:
        for name, sigma in SIGMAS.items():
            jobs = [(seed, sigma, args.minutos) for seed in seeds]
            report(name, list(pool.map(_live, jobs)))


if __name__ == "__main__":
    main()
