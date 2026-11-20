"""El piloto de la demo: mueve al jugador sin teclado, para `--demo`, las capturas y la
simulación sin ventana (ADR 0007)."""

import math
import random

from pygame.math import Vector2

from circlebh.balance import Balance
from circlebh.seeds import next_seed
from circlebh.world.clock import STEP
from circlebh.world.game import World

LAP_SECONDS = 4.0
"""Cuánto tarda el piloto en dar una vuelta completa."""


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
    """
    worlds = [World(balance, random.Random(seed))]
    for _ in range(round(seconds / STEP)):
        if worlds[-1].game_over:
            next_game = next_seed(seed, len(worlds), demo=True, fixed=True)
            worlds.append(World(balance, random.Random(next_game)))
        world = worlds[-1]
        world.update(pilot_intent(world.steps))
    return worlds
