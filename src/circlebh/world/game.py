"""La partida: todo lo que pasa en el plano, un paso de `STEP` a la vez (ADR 0005)."""

import math
import random
from dataclasses import replace

from pygame.math import Vector2

from circlebh.balance import Balance, RegenerateSpec
from circlebh.world.actions import Deliver, check_actions, step_actions, steps_of
from circlebh.world.cards import Loadout, Offer, apply, check_cards, deal
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
    CardChosen,
    Death,
    Donate,
    Event,
    ExperienceDrop,
    LevelUp,
    PlayerDeath,
    SectionStart,
    Spawn,
)
from circlebh.world.experience import Orb, check_experience, level_cost, step_orbs
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
from circlebh.world.weapons import Weapon, check_weapons, make_weapon


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
        check_experience(balance.experience)
        check_weapons(balance)
        check_cards(balance)
        start = balance.player.start_weapon
        self.arsenal: dict[str, Weapon] = (
            {start: make_weapon(balance.weapons[start], balance.sampling.spacing)}
            if armed
            else {}
        )
        """Las armas del jugador, por nombre, en el orden en que llegaron."""
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
        self.orbs: list[Orb] = []
        """Los puntos de experiencia que esperan en el plano."""
        self.experience = 0.0
        """Lo que llevas del nivel en curso."""
        self.level = 1
        """El nivel del jugador. Parte en 1."""
        self.pending_levels = 0
        """Los niveles subidos que todavía no se eligieron."""
        self.freezing = 0
        """Los pasos del frenado que quedan antes de repartir la mano."""
        self.hand: tuple[Offer, ...] = ()
        """Las tarjetas que esperan tu elección. Mientras haya, `update` no avanza."""
        self.rerolls = balance.level_up.rerolls
        """Cuántas veces puedes cambiar la mano entera."""
        self.banishes = balance.level_up.banishes
        """Cuántas tarjetas puedes sacar todavía de esta partida."""
        self.banished: set[str] = set()
        """Las tarjetas sacadas con banish: no vuelven en esta partida."""
        self._chosen: list[Event] = []
        """El `CardChosen` de la última elección, que sale en el `update` siguiente."""
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
    def weapons(self) -> list[Weapon]:
        """Las armas del jugador, en el orden en que llegaron."""
        return list(self.arsenal.values())

    @property
    def loadout(self) -> Loadout:
        """Lo que tiene el jugador, lo que una tarjeta puede cambiar."""
        return Loadout(
            {name: weapon.spec for name, weapon in self.arsenal.items()},
            self.player.spec,
            self.rerolls,
            self.banishes,
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
        fragmentos en su lugar, con su oleada. El que vale algo deja un punto de
        experiencia. El director sabe si queda alguien de la oleada en curso, vivo o en
        la cola, y cuántos cuerpos cuentan para el tope del infinito. Fuera del
        infinito, los puntos van hacia el jugador, y los que lo tocan suben su
        experiencia; en el infinito, se van sin recogerse. Lo que compró entra a la cola, y de ella aparecen hasta
        `spawning.max_per_step`, con el peligro del director, que empiezan a moverse en
        el paso siguiente; mientras hay una fusión en curso, las estrellas de la cola se
        descartan. La fusión da su paso: puede juntar las estrellas o hacer nacer la gran
        estrella roja. Recién entonces se revisa el contacto: matar a uno en el mismo paso
        en que te tocaría te salva. Si una bala o un enemigo lo toca, la partida termina;
        desde ahí, `update` no hace nada.

        `events` queda con lo que pasó en este paso: los avisos de ataque, los disparos
        y golpes de las armas, una muerte por cada enemigo que perdió su última línea,
        el punto de experiencia que dejó, cada nivel que subió el jugador, el inicio de
        cada sección, una aparición por cada enemigo que entró al plano y,
        si la partida terminó, la muerte del jugador con lo que lo tocó (ADR 0030).

        Al llenarse un nivel, el mundo da todavía `level_up.freeze_steps` pasos, y en el
        último reparte la mano con su `Random`. Desde ahí, `update` no avanza hasta
        `choose`, y no emite nada salvo el `CardChosen` de la elección anterior. Si
        mueres durante el frenado, la mano no sale.
        """
        self.events, self._chosen = self._chosen, []
        if self.game_over or self.hand:
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
            self.player.spec.charge,
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
            self._drop(enemy)
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
            # En el infinito no hay mejoras (ADR 0029): el borde queda quieto.
            self.orbs = []
        else:
            self._collect()
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
        if self.lethal:
            self._check_death(shot)
        if not self.game_over:
            self._freeze()

    def choose(self, index: int) -> None:
        """Elige la tarjeta `index` de la mano: aplica su cambio y cierra la mano. Si
        quedan niveles por elegir, reparte la siguiente al tiro, sin otro frenado.

        Lanza `IndexError` si no hay mano o si `index` no está en ella."""
        if not 0 <= index < len(self.hand):
            raise IndexError(f"no hay tarjeta {index} en una mano de {len(self.hand)}")
        offer = self.hand[index]
        state = apply(offer, self.loadout, self.balance.cards, self.balance.weapons)
        self._equip(state)
        self._chosen.append(CardChosen(offer))
        self._close_hand()

    def reroll(self) -> None:
        """Cambia la mano entera por otra, si hay mano y te quedan usos."""
        if not self.hand or self.rerolls <= 0:
            return
        self.rerolls -= 1
        self._deal()

    def banish(self, index: int) -> None:
        """Saca de la partida la tarjeta `index` de la mano, si te quedan usos: deja la
        mano y no vuelve a salir. Si la mano queda vacía, ese nivel se pierde."""
        if not self.hand or self.banishes <= 0:
            return
        card = self.hand[index].card
        self.banishes -= 1
        self.banished.add(card)
        self.hand = tuple(offer for offer in self.hand if offer.card != card)
        if not self.hand:
            self._close_hand()

    def _freeze(self) -> None:
        """Cuenta el frenado: empieza en el paso en que se llena un nivel, y en su
        último paso reparte la mano."""
        if self.freezing > 0:
            self.freezing -= 1
        elif self.pending_levels > 0:
            self.freezing = self.balance.level_up.freeze_steps
        else:
            return
        if self.freezing == 0:
            self._deal()

    def _deal(self) -> None:
        """Reparte la mano con la `Random` del mundo. Sin ninguna tarjeta con efecto,
        los niveles pendientes se pierden y el mundo sigue."""
        self.hand = deal(
            self.loadout,
            self.balance.cards,
            self.balance.level_up,
            self.banished,
            self.rng,
        )
        if not self.hand:
            self.pending_levels = 0

    def _close_hand(self) -> None:
        """Cierra la mano de un nivel. Si quedan otros, reparte la siguiente."""
        self.hand = ()
        self.pending_levels -= 1
        if self.pending_levels > 0:
            self._deal()

    def _equip(self, state: Loadout) -> None:
        """Deja al jugador y sus armas como dice `state`. Un arma que ya tenías cambia
        su `spec`; una nueva empieza sin balas."""
        for name, spec in state.weapons.items():
            if name in self.arsenal:
                self.arsenal[name].spec = spec
            else:
                self.arsenal[name] = make_weapon(spec, self.balance.sampling.spacing)
        self.player.spec = state.player
        self.rerolls = state.rerolls
        self.banishes = state.banishes

    def _check_death(self, shot: EnemyBullet | None) -> None:
        """Termina la partida si una bala lo tocó al empezar el paso o si un enemigo lo
        toca ahora."""
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

    def _drop(self, enemy: Enemy) -> None:
        """Si `enemy` vale algo, deja un punto de experiencia con su `threat` donde
        murió. El círculo, los fragmentos y las líneas sueltas valen 0. En el infinito no
        cae nada."""
        if enemy.spec.threat <= 0 or self.director.section.kind == "endless":
            return
        orb = Orb(enemy.position, enemy.spec.threat)
        self.orbs.append(orb)
        self.events.append(ExperienceDrop(orb))

    def _collect(self) -> None:
        """Los puntos dan su paso hacia el jugador, y los que lo tocan suben su
        experiencia. Cada nivel lleno emite un `LevelUp`, y lo que sobra pasa al
        siguiente."""
        self.orbs, collected = step_orbs(
            self.orbs,
            self.player,
            self.player.spec.charge,
            self.balance.experience,
            self.balance.charges,
        )
        self.experience += collected
        while self.experience >= (
            cost := level_cost(self.level, self.balance.experience)
        ):
            self.experience -= cost
            self.level += 1
            self.pending_levels += 1
            self.events.append(LevelUp(self.level))

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
