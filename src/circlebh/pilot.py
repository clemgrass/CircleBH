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


def simulate(balance: Balance, seconds: float, seed: int) -> int:
    """Juega `seconds` de partida con el piloto, sin ventana, y devuelve cuántas partidas
    hubo.

    Al morir, empieza otra al tiro, con la semilla que usaría la demo (`seed + n` en la
    partida `n`). La demo además muestra la muerte unos segundos; aquí no hace falta.
    """
    games = 0
    world = World(balance, random.Random(seed))
    for _ in range(round(seconds / STEP)):
        if world.game_over:
            games += 1
            next_game = next_seed(seed, games, demo=True, fixed=True)
            world = World(balance, random.Random(next_game))
        world.update(pilot_intent(world.steps))
    return games + 1
