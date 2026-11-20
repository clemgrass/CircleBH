"""La partida: todo lo que pasa en el plano, un paso de `STEP` a la vez (ADR 0005)."""

import random

from pygame.math import Vector2

from circlebh.balance import Balance
from circlebh.world.clock import STEP
from circlebh.world.collisions import circles_touch
from circlebh.world.enemy import Enemy, spawn_position
from circlebh.world.player import Player
from circlebh.world.weapons import PointWeapon, Weapon


class World:
    """El estado de una partida. Solo avanza con `update`."""

    def __init__(self, balance: Balance, rng: random.Random) -> None:
        self.balance = balance
        # El único azar de la partida (ADR 0005).
        self.rng = rng
        self.player = Player(balance.player)
        # Por ahora, un solo hexágono al empezar, fuera de la vista.
        position = spawn_position(self.player.position, balance.spawning.distance, rng)
        self.enemies = [Enemy(balance.enemies["hexagon"], position)]
        self.weapons: list[Weapon] = [PointWeapon(balance.point_weapon)]
        """Las armas del jugador. Por ahora, solo el arma punto."""
        self.game_over = False
        """Pasa a `True` cuando un enemigo toca al jugador, y no vuelve atrás."""
        self._steps = 0

    @property
    def steps(self) -> int:
        """Pasos dados en esta partida. Se detiene al morir."""
        return self._steps

    @property
    def elapsed(self) -> float:
        """Segundos de partida: los pasos dados por `STEP`, sin sumar error en cada paso."""
        return self._steps * STEP

    def update(self, intent: Vector2) -> None:
        """Avanza un paso, con la intención de movimiento del jugador (largo 0 a 1).

        El jugador se mueve primero, los enemigos van hacia donde quedó, y las armas
        golpean y disparan. Los enemigos sin líneas desaparecen, y recién entonces se
        revisa el contacto: matar a uno en el mismo paso en que te tocaría te salva. Si
        alguno lo toca, la partida termina; desde ahí, `update` no hace nada.
        """
        if self.game_over:
            return
        self._steps += 1
        self.player.step(intent)
        for enemy in self.enemies:
            enemy.step(self.player.position)
        for weapon in self.weapons:
            weapon.update(self.player.position, self.enemies)
        self.enemies = [enemy for enemy in self.enemies if enemy.alive]
        self.game_over = any(
            circles_touch(
                self.player.position, self.player.radius, e.position, e.radius
            )
            for e in self.enemies
        )
