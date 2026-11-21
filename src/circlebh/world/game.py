"""La partida: todo lo que pasa en el plano, un paso de `STEP` a la vez (ADR 0005)."""

import random

from pygame.math import Vector2

from circlebh.balance import Balance
from circlebh.world.clock import STEP
from circlebh.world.director import Director
from circlebh.world.enemy import Enemy, spawn_position
from circlebh.world.events import Death, Event
from circlebh.world.player import Player
from circlebh.world.swarm import step_swarm
from circlebh.world.weapons import PointWeapon, Weapon


class World:
    """El estado de una partida. Solo avanza con `update`."""

    def __init__(
        self,
        balance: Balance,
        rng: random.Random,
        *,
        lethal: bool = True,
        armed: bool = True,
    ) -> None:
        """`lethal=False` hace que el contacto no termine la partida, y `armed=False`
        deja al jugador sin armas. Los usan el escenario `panal`, el benchmark y la
        simulación, para mirar al enjambre sin que la partida termine."""
        self.balance = balance
        # El único azar de la partida (ADR 0005).
        self.rng = rng
        self.lethal = lethal
        self.player = Player(balance.player)
        self.enemies: list[Enemy] = []
        self.director = Director(balance.director, balance.enemies, rng)
        """Decide qué aparece y cuándo, con la forma del tema (ADR 0025)."""
        self.weapons: list[Weapon] = (
            [PointWeapon(balance.point_weapon)] if armed else []
        )
        """Las armas del jugador. Por ahora, solo el arma punto."""
        self.game_over = False
        """Pasa a `True` cuando un enemigo toca al jugador, y no vuelve atrás."""
        self.separations = 0
        """Cuántos pares corrigió la red de seguridad en toda la partida. Con la ley de
        cargas bien afinada, debería quedar en 0 (ADR 0021)."""
        self.events: list[Event] = []
        """Lo que pasó en el último `update` (ADR 0022). Se vacía al empezar cada uno."""
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

        El jugador se mueve primero, y el enjambre da su paso con el jugador donde quedó
        (`step_swarm`). Después las armas golpean y disparan. Los enemigos sin líneas
        desaparecen, y aparece lo que compró el director, que empieza a moverse en el
        paso siguiente. Recién entonces se revisa el contacto: matar a uno en el mismo paso
        en que te tocaría te salva. Si alguno lo toca, la partida termina; desde ahí,
        `update` no hace nada.

        `events` queda con lo que pasó en este paso: los disparos y golpes de las armas,
        y una muerte por cada enemigo que perdió su última línea.
        """
        self.events = []
        if self.game_over:
            return
        self._steps += 1
        self.player.step(intent)
        self.separations += step_swarm(
            self.enemies,
            self.player.position,
            self.balance.player.charge,
            self.balance.charges,
        )
        for weapon in self.weapons:
            self.events += weapon.update(self.player.position, self.enemies)
        self.events += [Death(enemy) for enemy in self.enemies if not enemy.alive]
        self.enemies = [enemy for enemy in self.enemies if enemy.alive]
        for name in self.director.update(self._steps):
            self._spawn(name)
        self.game_over = self.lethal and any(
            enemy.touches(self.player.position, self.player.radius)
            for enemy in self.enemies
        )

    def _spawn(self, name: str) -> None:
        """Agrega un enemigo del tipo `name` a `spawning.distance` del jugador, fuera de
        la vista."""
        spawning = self.balance.spawning
        position = spawn_position(self.player.position, spawning.distance, self.rng)
        self.enemies.append(Enemy(self.balance.enemies[name], position))
