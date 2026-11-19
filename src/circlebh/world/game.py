"""La partida: todo lo que pasa en el plano, un paso de `STEP` a la vez (ADR 0005)."""

import random

from pygame.math import Vector2

from circlebh.balance import Balance
from circlebh.world.player import Player


class World:
    """El estado de una partida. Solo avanza con `update`."""

    def __init__(self, balance: Balance, rng: random.Random) -> None:
        self.balance = balance
        # El único azar de la partida (ADR 0005). Todavía nada lo usa.
        self.rng = rng
        self.player = Player(balance.player)

    def update(self, intent: Vector2) -> None:
        """Avanza un paso, con la intención de movimiento del jugador (largo 0 a 1)."""
        self.player.step(intent)
