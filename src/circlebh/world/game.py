"""La partida: todo lo que pasa en el plano, un paso de `STEP` a la vez (ADR 0005)."""

import random

from pygame.math import Vector2

from circlebh.balance import Balance
from circlebh.world.actions import step_actions
from circlebh.world.clock import STEP
from circlebh.world.director import Director, Purchase
from circlebh.world.enemy import Enemy
from circlebh.world.enemy_bullets import EnemyBullet, bullet_hits_player, step_bullets
from circlebh.world.events import Death, Event
from circlebh.world.figures import check_shapes
from circlebh.world.merge import Merge, check_merge
from circlebh.world.player import Player
from circlebh.world.spawning import SpawnQueue, check_formations, place_formation
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
        self.director = Director(
            balance.director, balance.enemies, balance.spawning, rng
        )
        """Decide qué aparece y cuándo, con la forma del tema (ADR 0025)."""
        check_shapes(balance.enemies)
        check_merge(balance)
        self.merge = Merge(balance.merge, balance.enemies, balance.director.bpm)
        """La fusión de las estrellas en la gran estrella roja."""
        check_formations(balance)
        self.queue = SpawnQueue()
        """Lo comprado que espera aparecer, con su lugar relativo al jugador. Sale de a
        `spawning.max_per_step` por paso."""
        self.weapons: list[Weapon] = (
            [PointWeapon(balance.point_weapon)] if armed else []
        )
        """Las armas del jugador. Por ahora, solo el arma punto."""
        self.enemy_bullets: list[EnemyBullet] = []
        """Las balas de los enemigos. Atraviesan a los demás enemigos y matan al jugador."""
        self.game_over = False
        """Pasa a `True` cuando un enemigo o una bala enemiga toca al jugador, y no vuelve
        atrás."""
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

        El jugador se mueve primero, y las balas enemigas avanzan: si alguna lo cruzó en
        este paso, lo mató. Después, las acciones de los enemigos miran dónde quedó, y las
        balas que disparan empiezan a moverse en el paso siguiente. El enjambre da su paso
        (`step_swarm`), y las armas golpean y disparan. Los enemigos sin líneas
        desaparecen. Lo que compró el director entra a la cola, y de ella aparecen hasta
        `spawning.max_per_step`, que empiezan a moverse en el paso siguiente; mientras
        hay una fusión en curso, las estrellas de la cola se descartan. La fusión da su
        paso: puede juntar las estrellas o hacer nacer la gran estrella roja. Recién
        entonces se revisa el contacto: matar a uno en el mismo paso en que te tocaría te
        salva. Si una bala o un enemigo lo toca, la partida termina; desde ahí, `update`
        no hace nada.

        `events` queda con lo que pasó en este paso: los avisos de ataque, los disparos
        y golpes de las armas, y una muerte por cada enemigo que perdió su última línea.
        """
        self.events = []
        if self.game_over:
            return
        self._steps += 1
        self.player.step(intent)
        bullet = self.balance.enemy_bullet
        self.enemy_bullets = step_bullets(
            self.enemy_bullets, self.player.position, self.balance.spawning.distance
        )
        shot = any(
            bullet_hits_player(b, self.player, bullet.radius)
            for b in self.enemy_bullets
        )
        self.events += step_actions(
            self.enemies, self.player.position, self.rng, self.enemy_bullets, bullet
        )
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
        for purchase in self.director.update(self._steps):
            self._enqueue(purchase)
        for name, offset in self.queue.pop(self.balance.spawning.max_per_step):
            if not self.merge.allows(name):
                continue
            position = self.player.position + offset
            self.enemies.append(Enemy(self.balance.enemies[name], position))
        self.enemies = self.merge.update(
            self._steps, self.enemies, self.player.position
        )
        self.game_over = self.lethal and (
            shot
            or any(
                enemy.touches(self.player.position, self.player.radius)
                for enemy in self.enemies
            )
        )

    def _enqueue(self, purchase: Purchase) -> None:
        """Elige dónde nace cada miembro de `purchase`, relativo al jugador, y lo pone en
        la cola. Cuentan los vivos y los que ya esperan, para que una ráfaga se reparta
        entre los cuadrantes."""
        here = self.player.position
        enemies = self.balance.enemies
        occupied = [(enemy.position - here, enemy.radius) for enemy in self.enemies]
        occupied += [(offset, enemies[name].radius) for name, offset in self.queue]
        offsets = place_formation(
            purchase.formation,
            purchase.count,
            enemies[purchase.enemy].radius,
            occupied,
            self.balance.spawning,
            self.balance.charges.core_reach,
            self.rng,
        )
        self.queue.push((purchase.enemy, offset) for offset in offsets)
