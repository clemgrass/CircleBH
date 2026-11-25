"""La partida: todo lo que pasa en el plano, un paso de `STEP` a la vez (ADR 0005)."""

import math
import random
from dataclasses import replace

from pygame.math import Vector2

from circlebh.balance import Balance, RegenerateSpec
from circlebh.world.actions import Deliver, check_actions, step_actions, steps_of
from circlebh.world.clock import STEP
from circlebh.world.critical_mass import (
    CriticalMass,
    check_critical_mass,
    heavy_direction,
)
from circlebh.world.director import Director, Purchase, body_weight
from circlebh.world.enemy import Enemy, check_masses
from circlebh.world.enemy_bullets import EnemyBullet, bullet_hits_player, step_bullets
from circlebh.world.events import (
    Death,
    Donate,
    Event,
    PlayerDeath,
    SectionStart,
    Spawn,
)
from circlebh.world.figures import check_shapes
from circlebh.world.merge import Merge, check_merge
from circlebh.world.player import Player
from circlebh.world.regrowth import absorb
from circlebh.world.spawning import (
    Queued,
    SpawnQueue,
    check_formations,
    place_formation,
)
from circlebh.world.split import check_splits, fragments
from circlebh.world.swarm import step_swarm
from circlebh.world.weapons import ProjectileWeapon, Weapon, check_weapons


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
        # Primero cada enemigo, después el tema que los usa: el error de un enemigo
        # nombra el campo exacto, y el del mazo, solo al enemigo.
        check_shapes(balance.enemies)
        check_actions(balance.enemies)
        check_masses(balance.enemies)
        check_splits(balance.enemies)
        self.director = Director(
            balance.director, balance.enemies, balance.spawning, rng
        )
        """Decide qué aparece y cuándo, con la forma del tema (ADR 0025)."""
        check_merge(balance)
        self.merge = Merge(balance.merge, balance.enemies, balance.director.bpm)
        """La fusión de las estrellas en la gran estrella roja."""
        check_critical_mass(balance)
        self.critical_mass = CriticalMass(balance.critical_mass, balance.director.bpm)
        """Cuándo aparece el círculo que reparte al enjambre."""
        check_formations(balance)
        self.queue = SpawnQueue()
        """Lo comprado que espera aparecer, con su lugar relativo al jugador. Sale de a
        `spawning.max_per_step` por paso."""
        check_weapons(balance)
        start = balance.weapons[balance.player.start_weapon]
        self.weapons: list[Weapon] = [ProjectileWeapon(start)] if armed else []
        """Las armas del jugador. Por ahora, solo la inicial."""
        self.enemy_bullets: list[EnemyBullet] = []
        """Las balas de los enemigos. Atraviesan a los demás enemigos y matan al jugador."""
        self.game_over = False
        """Pasa a `True` cuando un enemigo o una bala enemiga toca al jugador, y no vuelve
        atrás. En ese paso, `events` trae el `PlayerDeath`."""
        self.separations = 0
        """Cuántos pares corrigió la red de seguridad en toda la partida. Con la ley de
        cargas bien afinada, debería quedar en 0 (ADR 0021)."""
        self.events: list[Event] = []
        """Lo que pasó en el último `update` (ADR 0022). Se vacía al empezar cada uno."""
        self.ghosts: list[tuple[tuple[Vector2, Vector2], int]] = []
        """Las líneas sueltas absorbidas, con el paso en que las absorbieron. Ya no están
        en el plano: quedan `regrow.fade` segundos para que el render las apague mientras
        el hueco del herido se enciende (decisión 66)."""
        self._steps = 0
        self._endless_steps = 0
        self._announced = -1
        """La última sección que ya emitió su `SectionStart`."""

    @property
    def steps(self) -> int:
        """Pasos dados en esta partida. Se detiene al morir."""
        return self._steps

    @property
    def endless_steps(self) -> int:
        """Pasos dados en el modo infinito: 0 si no llegaste. Se detiene al morir."""
        return self._endless_steps

    @property
    def bodies(self) -> int:
        """Los cuerpos que cuentan para el tope del infinito: los vivos y los de la cola,
        cada uno por los que puede llegar a ser (`body_weight`)."""
        enemies = self.balance.enemies
        return sum(body_weight(enemy.spec, enemies) for enemy in self.enemies) + sum(
            body_weight(enemies[item.enemy], enemies) for item in self.queue
        )

    @property
    def elapsed(self) -> float:
        """Segundos de partida: los pasos dados por `STEP`, sin sumar error en cada paso."""
        return self._steps * STEP

    def update(self, intent: Vector2) -> None:
        """Avanza un paso, con la intención de movimiento del jugador (largo 0 a 1).

        El jugador se mueve primero, y las balas enemigas avanzan: si alguna lo cruzó en
        este paso, lo mató. Después, las acciones de los enemigos miran dónde quedó, y las
        balas que disparan empiezan a moverse en el paso siguiente. El enjambre da su paso
        (`step_swarm`), y las armas golpean y disparan. Las líneas que donó un médico
        pasan a ser líneas sueltas, y los heridos absorben las que tocan: después de las
        balas, para que un herido que murió en este paso no se cure. Los enemigos sin
        líneas desaparecen, y el que se parte al morir, como el divisor, deja sus
        fragmentos en su lugar, con su oleada. El director sabe si queda alguien de la
        oleada en curso, vivo o en la cola, y cuántos cuerpos cuentan para el tope del
        infinito. Lo que compró entra a la cola, y de ella aparecen hasta
        `spawning.max_per_step`, con el peligro del director, que empiezan a moverse en
        el paso siguiente; mientras hay una fusión en curso, las estrellas de la cola se
        descartan. La fusión da su paso: puede juntar las estrellas o hacer nacer la gran
        estrella roja. Recién entonces se revisa el contacto: matar a uno en el mismo paso
        en que te tocaría te salva. Si una bala o un enemigo lo toca, la partida termina;
        desde ahí, `update` no hace nada.

        `events` queda con lo que pasó en este paso: los avisos de ataque, los disparos
        y golpes de las armas, una muerte por cada enemigo que perdió su última línea,
        el inicio de cada sección, una aparición por cada enemigo que entró al plano y,
        si la partida terminó, la muerte del jugador con lo que lo tocó (ADR 0030).
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
        shot = next(
            (
                b
                for b in self.enemy_bullets
                if bullet_hits_player(b, self.player, bullet.radius)
            ),
            None,
        )
        self.events += step_actions(
            self.enemies,
            self.player.position,
            self.rng,
            self.enemy_bullets,
            bullet,
            self._steps,
        )
        self.separations += step_swarm(
            self.enemies,
            self.player.position,
            self.player.velocity,
            self.balance.player.charge,
            self.balance.charges,
        )
        for weapon in self.weapons:
            self.events += weapon.update(self.player.position, self.enemies)
        for event in self.events:
            if isinstance(event, Donate):
                self._release(event)
        self._absorb()
        dead = [enemy for enemy in self.enemies if not enemy.alive]
        self.events += [Death(enemy) for enemy in dead]
        self.enemies = [enemy for enemy in self.enemies if enemy.alive]
        for enemy in dead:
            self._split(enemy)
        # Fuera de una oleada no hace falta recorrer el plano y la cola.
        alive = self.director.waiting and self._wave_alive()
        updates = self.director.update(
            self._steps, wave_alive=alive, bodies=self.bodies
        )
        for purchase in updates:
            self._enqueue(purchase)
        sections = self.balance.director.sections
        for index in range(self._announced + 1, self.director.section_index + 1):
            self.events.append(SectionStart(index, sections[index]))
        self._announced = self.director.section_index
        if self.director.section.kind == "endless":
            self._endless_steps += 1
        danger = self.director.danger
        for item in self.queue.pop(self.balance.spawning.max_per_step):
            if not self.merge.allows(item.enemy):
                continue
            position = self.player.position + item.offset
            enemy = Enemy(self.balance.enemies[item.enemy], position, danger)
            enemy.wave = item.wave
            self.enemies.append(enemy)
            self.events.append(Spawn(enemy))
        merged = self.merge.present
        self.enemies = self.merge.update(
            self._steps, self.enemies, self.player.position
        )
        if self.merge.present is not None and self.merge.present is not merged:
            self.events.append(Spawn(self.merge.present))
        self._check_critical_mass()
        if not self.lethal:
            return
        # La bala mató al empezar el paso. El contacto se revisa recién ahora.
        cause: Enemy | EnemyBullet | None = shot
        if cause is None:
            cause = next(
                (
                    enemy
                    for enemy in self.enemies
                    if enemy.touches(self.player.position, self.player.radius)
                ),
                None,
            )
        if cause is not None:
            self.game_over = True
            self.events.append(PlayerDeath(cause))

    def _release(self, event: Donate) -> None:
        """Convierte la línea que donó el médico en una línea suelta, donde estaba, con
        su largo, su orientación y la velocidad del médico. Nace en este paso, sin pasar
        por la cola, y va al paciente desde el siguiente."""
        name = next(
            a.stray for a in event.enemy.spec.actions if isinstance(a, RegenerateSpec)
        )
        a, b = event.line
        stray = Enemy(
            replace(self.balance.enemies[name], radius=a.distance_to(b) / 2),
            (a + b) / 2,
        )
        stray.angle = stray.previous_angle = math.atan2(b.y - a.y, b.x - a.x)
        stray.velocity = Vector2(event.enemy.velocity)
        for action in stray.actions:
            if isinstance(action, Deliver):
                action.patient, action.donor = event.patient, event.enemy
        self.enemies.append(stray)
        self.events.append(Spawn(stray))

    def _split(self, enemy: Enemy) -> None:
        """Si `enemy` se parte al morir, suma sus fragmentos. Nacen en este paso, sin
        pasar por la cola, y se mueven desde el siguiente. El que tocaría al jugador no
        nace."""
        if not enemy.spec.split_into:
            return
        spec = self.balance.enemies[enemy.spec.split_into]
        children = fragments(enemy, spec, self.player.position, self.player.radius)
        for child in children:
            # Los fragmentos de una oleada son parte de ella: no se limpia sin ellos.
            child.wave = enemy.wave
        self.enemies += children
        self.events += [Spawn(child) for child in children]

    def _wave_alive(self) -> bool:
        """Si queda algún enemigo de la oleada en curso, vivo o esperando en la cola."""
        wave = self.director.section_index
        return any(enemy.wave == wave for enemy in self.enemies) or any(
            item.wave == wave for item in self.queue
        )

    def _absorb(self) -> None:
        """Los heridos absorben las líneas sueltas que tocan. Las absorbidas salen del
        plano sin morir, y quedan como fantasmas mientras se apagan."""
        fade = steps_of(self.balance.regrow.fade)
        self.ghosts = [g for g in self.ghosts if self._steps - g[1] < fade]
        regrown, absorbed = absorb(self.enemies, self._steps)
        self.events += regrown
        for stray in absorbed:
            self.enemies.remove(stray)
            [line] = stray.lines()
            self.ghosts.append((line, self._steps))

    def _check_critical_mass(self) -> None:
        """Si el enjambre se cargó hacia un lado, compra un círculo que lo reparta.

        Cuentan los vivos que siguen al jugador: no los anclados ni los fantasmas. El
        círculo está presente si hay uno vivo o en la cola. Nace detrás del grupo, hacia
        donde está cargado, para cruzarlo desde afuera (decisión 56)."""
        name = self.balance.critical_mass.enemy
        spec = self.balance.enemies[name]
        # `is` y no `==`: comparar la dataclass campo por campo, contra cada enemigo y en
        # cada paso, hacía notar el costo en el benchmark del enjambre.
        present = any(enemy.spec is spec for enemy in self.enemies) or any(
            item.enemy == name for item in self.queue
        )
        here = self.player.position
        offsets = [
            enemy.position - here
            for enemy in self.enemies
            if not (enemy.spec.anchored or enemy.spec.phantom or enemy.stray)
        ]
        if self.critical_mass.update(self._steps, present, offsets):
            heavy = heavy_direction(offsets)
            angle = None if heavy is None else math.atan2(heavy.y, heavy.x)
            self._enqueue(Purchase(name, "single", 1), angle)

    def _enqueue(self, purchase: Purchase, angle: float | None = None) -> None:
        """Elige dónde nace cada miembro de `purchase`, relativo al jugador, y lo pone en
        la cola. Cuentan los vivos y los que ya esperan, para que una ráfaga se reparta
        entre los cuadrantes. Con `angle`, nace hacia ese ángulo en vez de en el
        cuadrante más vacío."""
        here = self.player.position
        enemies = self.balance.enemies
        # Los fantasmas no ocupan lugar: los demás los atraviesan.
        occupied = [
            (enemy.position - here, enemy.radius)
            for enemy in self.enemies
            if not enemy.spec.phantom
        ]
        occupied += [(item.offset, enemies[item.enemy].radius) for item in self.queue]
        offsets = place_formation(
            purchase.formation,
            purchase.count,
            enemies[purchase.enemy].radius,
            occupied,
            self.balance.spawning,
            self.balance.charges.core_reach,
            self.rng,
            angle,
        )
        self.queue.push(Queued(purchase.enemy, o, purchase.wave) for o in offsets)
