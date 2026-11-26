"""Los pilotos: mueven al jugador sin teclado.

- **El de la demo (P0)** da vueltas, para `--demo`, las capturas y la simulación sin
  ventana (ADR 0007).
- **El que esquiva (P1)** huye con un campo de fuerzas y un error σ, para medir el
  balance (ADR 0030).
"""

import math
import random
from collections.abc import Callable

from pygame.math import Vector2

from circlebh.balance import Balance
from circlebh.seeds import next_seed
from circlebh.world.clock import STEP
from circlebh.world.game import World

LAP_SECONDS = 4.0
"""Cuánto tarda el piloto de la demo en dar una vuelta completa."""

# P1. Son del piloto, no del juego: no van al balance ni a la configuración.
REACH = 250.0
"""Más lejos que esto, un enemigo o una bala no empuja a P1."""
NEAREST = 4.0
"""La distancia mínima en `1/d²`, para que la fuerza no se vaya al infinito."""
BULLET_WEIGHT = 4.0
"""Cuánto más empuja una bala que un enemigo."""
LOOKAHEAD = 0.3
"""Cuántos segundos adelante mira P1 cada bala."""
NOISE_STEPS = 6
"""Cada cuántos pasos se sortea de nuevo el error de P1: 0,1 s."""


def pilot_intent(step: int) -> Vector2:
    """La intención en el paso `step`: un círculo antihorario que parte hacia +x.

    La dirección gira a velocidad constante, así que el jugador recorre un círculo.
    """
    angle = math.tau * step * STEP / LAP_SECONDS
    return Vector2(math.cos(angle), math.sin(angle))


def simulate(balance: Balance, seconds: float, seed: int) -> list[float]:
    """Juega `seconds` de partida con el piloto, sin ventana, y devuelve cuánto duró cada
    partida, en orden. La última queda cortada al llegar a `seconds`."""
    return [world.elapsed for world in simulate_worlds(balance, seconds, seed)]


def simulate_worlds(balance: Balance, seconds: float, seed: int) -> list[World]:
    """Como `simulate`, pero devuelve las partidas mismas, para revisar su estado final.

    Al morir, empieza otra al tiro, con la semilla que usaría la demo (`seed + n` en la
    partida `n`). La demo además muestra la muerte unos segundos; aquí no hace falta.
    Cada mano se elige al azar con una `Random` propia, sembrada con la semilla de la
    partida, como en la demo.
    """
    return _play(
        balance, seconds, seed, lambda _: lambda world: pilot_intent(world.steps)
    )


type Pilot = Callable[[World], Vector2]
"""Un piloto: la intención del jugador en el paso en que está el mundo."""


def _play(
    balance: Balance,
    seconds: float,
    seed: int,
    make_pilot: Callable[[random.Random], Pilot],
) -> list[World]:
    """Juega `seconds` con el piloto que arma `make_pilot` y reinicia al morir.

    Cada partida trae su `Random` propia, sembrada con su semilla: elige las tarjetas, y
    el piloto la recibe por si sortea algo.
    """
    worlds = [World(balance, random.Random(seed))]
    chooser = random.Random(seed)
    pilot = make_pilot(chooser)
    for _ in range(round(seconds / STEP)):
        if worlds[-1].game_over:
            next_game = next_seed(seed, len(worlds), demo=True, fixed=True)
            worlds.append(World(balance, random.Random(next_game)))
            chooser = random.Random(next_game)
            pilot = make_pilot(chooser)
        world = worlds[-1]
        choose_at_random(world, chooser)
        world.update(pilot(world))
    return worlds


class DodgingPilot:
    """P1: huye de lo que lo puede matar, con un error angular de desviación `sigma`
    (ADR 0030).

    Cada enemigo lo empuja con `1/d²`, donde `d` es la distancia entre el borde del
    jugador y el círculo envolvente del enemigo, como las cargas del ADR 0021. Cada bala
    enemiga empuja `BULLET_WEIGHT` veces más, desde donde va a estar en `LOOKAHEAD`
    segundos. Sin empuje, da vueltas como el piloto de la demo.

    La habilidad es el error: la dirección se gira un ángulo normal de desviación
    `sigma`, en radianes, sorteado cada `NOISE_STEPS` pasos con `chooser`, una `Random`
    propia, nunca la del mundo (ADR 0005). La misma `Random` elige las tarjetas.
    """

    def __init__(self, sigma: float, chooser: random.Random) -> None:
        if sigma < 0:
            raise ValueError(f"sigma no puede ser negativo: {sigma}")
        self.sigma = sigma
        self.chooser = chooser
        self.error = 0.0
        """El ángulo que gira la dirección hasta el próximo sorteo."""

    def __call__(self, world: World) -> Vector2:
        """La intención en este paso: hacia donde empujan los peligros, girada por el
        error."""
        if world.steps % NOISE_STEPS == 0:
            self.error = self.chooser.gauss(0.0, self.sigma)
        here = world.player.position
        reach = world.player.radius
        push = Vector2()
        for enemy in world.enemies:
            push += _repel(here, enemy.position, reach + enemy.radius, 1.0)
        for bullet in world.enemy_bullets:
            ahead = bullet.position + bullet.velocity * LOOKAHEAD
            push += _repel(here, ahead, reach, BULLET_WEIGHT)
        if push.length_squared() == 0:
            return pilot_intent(world.steps)
        return push.normalize().rotate_rad(self.error)


def _repel(here: Vector2, source: Vector2, contact: float, weight: float) -> Vector2:
    """El empuje de `source` sobre `here`: `weight/d²` desde `source`, donde `d` es la
    distancia que falta para que se toquen (`contact` es la suma de los radios).

    `d` no baja de `NEAREST`, para que la fuerza no se vaya al infinito al tocarse. Más
    allá de `REACH`, o justo encima, sin dirección, no empuja.
    """
    offset = here - source
    if offset.length_squared() == 0:
        return Vector2()
    gap = offset.length() - contact
    if gap > REACH:
        return Vector2()
    return offset.normalize() * weight / max(gap, NEAREST) ** 2


def simulate_dodging(
    balance: Balance, seconds: float, seed: int, sigma: float
) -> list[World]:
    """Como `simulate_worlds`, pero juega P1 con error `sigma`. Su `Random` se siembra
    con la semilla de cada partida, y con ella sortea el error y elige las tarjetas."""
    return _play(balance, seconds, seed, lambda chooser: DodgingPilot(sigma, chooser))


def choose_at_random(world: World, rng: random.Random) -> None:
    """Si hay mano, elige una tarjeta al azar con `rng`, no con la `Random` del mundo
    (spec de la 0.3.0, decisión 13): así, elegir no cambia lo que el mundo sortea
    después. Sin mano, no hace nada ni saca números."""
    if world.hand:
        world.choose(pick_at_random(world, rng))


def pick_at_random(world: World, rng: random.Random) -> int:
    """El índice que elegiría `choose_at_random`, sin elegirlo: la demo lo marca y lo
    anima antes de elegir. Saca de `rng` lo mismo, así que la demo juega la misma
    partida que la simulación."""
    return rng.randrange(len(world.hand))
