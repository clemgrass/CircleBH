"""Las acciones: lo que un enemigo hace y no es una fuerza (ADR 0021).

Los patrones suman aceleraciones. Una acción, en cambio, es una máquina de estados
chica, con sus tiempos en el balance. Puede apagar los patrones (`controls_motion`) y
fijar la velocidad (`velocity`) o el giro (`omega`) del enemigo.

Todas las acciones se actualizan antes del paso del enjambre, con las posiciones del
inicio del paso. Cada una cambia solo su propio estado. El orden de la lista importa
solo para lo que sacan de la `Random`, y es siempre el de aparición.
"""

import math
import random
from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import Enum, auto
from typing import TYPE_CHECKING

from pygame.math import Vector2

from circlebh.balance import (
    ActionSpec,
    ChargeSpec,
    DeliverSpec,
    EnemyBulletSpec,
    EnemySpec,
    RegenerateSpec,
    SegmentShape,
    SpiralSpec,
    StarPolygonShape,
    VolleySpec,
)
from circlebh.world.clock import STEP
from circlebh.world.collisions import segment_touches_circle
from circlebh.world.enemy_bullets import EnemyBullet
from circlebh.world.events import Donate, Event, Regrow, Telegraph
from circlebh.world.figures import line_vertices
from circlebh.world.polygon import vertex
from circlebh.world.rigid import rotate

if TYPE_CHECKING:
    from circlebh.world.enemy import Enemy


@dataclass(frozen=True)
class ActionContext:
    """Lo que una acción puede mirar en este paso."""

    player_position: Vector2
    enemies: Sequence[Enemy]
    """Todos los enemigos vivos, también el que actúa."""
    rng: random.Random
    """La `Random` del mundo, el único azar de la partida (ADR 0005)."""
    bullets: list[EnemyBullet]
    """Las balas enemigas del mundo. Una acción que dispara agrega las suyas aquí."""
    bullet_spec: EnemyBulletSpec
    """Cómo son esas balas."""
    steps: int = 0
    """El paso del mundo. Lo guarda la línea que vuelve, para su fundido."""


class Action(ABC):
    """La base de toda acción."""

    @abstractmethod
    def update(self, enemy: Enemy, context: ActionContext) -> list[Event]:
        """Avanza un paso la acción de `enemy`, y devuelve lo que pasó."""

    @property
    def controls_motion(self) -> bool:
        """Si apaga los patrones: el enemigo siente solo su roce."""
        return False

    @property
    def velocity(self) -> Vector2 | None:
        """La velocidad que la acción le fija al enemigo, sin tope, o `None`."""
        return None

    @property
    def omega(self) -> float | None:
        """La velocidad angular que la acción le fija al enemigo, o `None`: entonces
        gira con su `spin`."""
        return None

    @property
    def charge_scale(self) -> float | None:
        """Por cuánto multiplica la acción la carga del enemigo, o `None`: entonces la
        carga es la de siempre. Con −1, el enemigo atrae en vez de repeler, con la misma
        ley de cargas (decisión 57)."""
        return None


def steps_of(seconds: float) -> int:
    """Cuántos pasos dura una etapa de `seconds`. Se cuenta en pasos y no en segundos,
    para que restar `STEP` no acumule error."""
    return round(seconds / STEP)


def clear_line(
    start: Vector2, end: Vector2, radius: float, others: Sequence[Enemy]
) -> bool:
    """Si un cuerpo de `radius` puede ir en línea recta de `start` a `end` sin tocar el
    círculo envolvente de ninguno de `others`.

    Lo que barre el cuerpo es una cápsula: el tramo engordado en `radius`. Tocar un
    círculo de radio `ρ` con ella es lo mismo que tocar con el tramo un círculo de radio
    `ρ + radius` (la suma de Minkowski).
    """
    return not any(
        segment_touches_circle(start, end, other.position, other.radius + radius)
        for other in others
    )


class ChargeState(Enum):
    WATCHING = auto()
    """Lo mueven sus patrones, y busca la recta libre hasta el jugador."""
    TELEGRAPHING = auto()
    """Avisa: sigue mirando al jugador y retrocede, como un resorte que se comprime."""
    CHARGING = auto()
    """Embiste a `speed` en la dirección que eligió al soltarse, sin corregir el rumbo."""
    RECOVERING = auto()
    """Lo mueven sus patrones otra vez, pero todavía no puede avisar."""


class Charge(Action):
    """La embestida del triángulo: observa, avisa, embiste y se recupera.

    Te mira siempre con una punta, salvo al embestir. Solo avisa con el jugador a
    `watch_distance` o menos y con la recta libre. Al terminar el aviso se suelta hacia
    donde está el jugador, o, con probabilidad `lead_chance`, a `lead_angle` de él, hacia
    el lado con menos enemigos (decisión 30 de la spec de la 0.2.0). Si al soltarse la
    recta está tapada, no embiste y vuelve a observar.
    """

    def __init__(self, spec: ChargeSpec, cadence: float = 1.0) -> None:
        """Con `cadence` mayor que 1, se recupera antes: es el peligro del infinito. El
        aviso y la embestida no cambian, para que se sigan pudiendo leer y esquivar."""
        self.spec = spec
        self.state = ChargeState.WATCHING
        self.direction = Vector2()
        """Hacia dónde embiste, unitaria. Se elige al soltarse."""
        self._durations = {
            ChargeState.TELEGRAPHING: steps_of(spec.telegraph),
            ChargeState.CHARGING: steps_of(spec.duration),
            ChargeState.RECOVERING: steps_of(spec.cooldown / cadence),
        }
        self._left = 0
        """Los pasos que le quedan a la etapa, contando el actual."""
        self._velocity: Vector2 | None = None
        self._omega: float | None = None

    @property
    def controls_motion(self) -> bool:
        return self.state in (ChargeState.TELEGRAPHING, ChargeState.CHARGING)

    @property
    def velocity(self) -> Vector2 | None:
        return self._velocity

    @property
    def omega(self) -> float | None:
        return self._omega

    def update(self, enemy: Enemy, context: ActionContext) -> list[Event]:
        events = self._advance(enemy, context)
        self._move(enemy, context)
        return events

    def _advance(self, enemy: Enemy, context: ActionContext) -> list[Event]:
        """Cuenta los pasos de la etapa y pasa a la siguiente cuando se acaban."""
        if self.state is not ChargeState.WATCHING:
            self._left -= 1
            if self._left > 0:
                return []
            if self.state is ChargeState.TELEGRAPHING:
                aim = self._launch(enemy, context)
                if aim is not None:
                    self.direction = aim
                    self._enter(ChargeState.CHARGING)
                    return []
                self._enter(ChargeState.WATCHING)
            elif self.state is ChargeState.CHARGING:
                self._enter(ChargeState.RECOVERING)
            else:
                self._enter(ChargeState.WATCHING)
        # Al terminar la recuperación, ya mira en este mismo paso.
        if self.state is ChargeState.WATCHING and self._sees(enemy, context):
            self._enter(ChargeState.TELEGRAPHING)
            return [Telegraph(enemy)]
        return []

    def _move(self, enemy: Enemy, context: ActionContext) -> None:
        """La velocidad y el giro que fija en este paso, según la etapa."""
        if self.state is ChargeState.CHARGING:
            self._velocity = self.direction * self.spec.speed
            self._omega = 0.0
            return
        to_player = context.player_position - enemy.position
        self._omega = self._turn(enemy.angle, to_player)
        if self.state is ChargeState.TELEGRAPHING and to_player.length_squared() > 0:
            self._velocity = -to_player.normalize() * self._recoil_speed()
        else:
            self._velocity = None

    def _turn(self, angle: float, to_player: Vector2) -> float:
        """La velocidad angular que lleva su primera punta hacia el jugador, a lo más
        `turn_rate`. Esa punta está en `π/2` del marco del enemigo (`polygon.py`), así
        que apunta al jugador con `θ = atan2(d) − π/2`. Gira por el lado más corto."""
        if to_player.length_squared() == 0:
            return 0.0
        target = math.atan2(to_player.y, to_player.x) - math.pi / 2
        turn = math.remainder(target - angle, math.tau) / STEP
        return max(-self.spec.turn_rate, min(self.spec.turn_rate, turn))

    def _recoil_speed(self) -> float:
        """La rapidez del retroceso en este paso del aviso.

        El retroceso sigue `x(s) = recoil · sen(π·s/2)`, con `s` de 0 a 1 a lo largo del
        aviso: rápido al empezar, y quieto justo antes de soltarse, como un resorte que
        se comprime. En el paso `k` de `n`, avanza `x((k+1)/n) − x(k/n)`, así que la suma
        de todos los pasos da `recoil` exacto.
        """
        n = self._durations[ChargeState.TELEGRAPHING]
        k = n - self._left

        def x(step: int) -> float:
            return self.spec.recoil * math.sin(math.pi / 2 * step / n)

        return (x(k + 1) - x(k)) / STEP

    def _launch(self, enemy: Enemy, context: ActionContext) -> Vector2 | None:
        """Hacia dónde se suelta, unitaria, o `None` si la recta al jugador está tapada.

        Con probabilidad `lead_chance` se desvía `lead_angle` hacia el lado con menos
        enemigos cerca del jugador. Si esa recta está tapada, va directo.
        """
        player = context.player_position
        to_player = player - enemy.position
        others = [other for other in context.enemies if other is not enemy]
        if to_player.length_squared() == 0 or not clear_line(
            enemy.position, player, enemy.radius, others
        ):
            return None
        direct = to_player.normalize()
        if context.rng.random() >= self.spec.lead_chance:
            return direct
        side = self._emptier_side(direct, player, others, context.rng)
        lead = rotate(direct, side * self.spec.lead_angle)
        end = enemy.position + lead * to_player.length()
        return lead if clear_line(enemy.position, end, enemy.radius, others) else direct

    def _emptier_side(
        self,
        direct: Vector2,
        player: Vector2,
        others: Sequence[Enemy],
        rng: random.Random,
    ) -> int:
        """`+1` si hay menos enemigos a la izquierda de `direct` (girar antihorario), y
        `−1` si hay menos a la derecha. Cuentan los que están a `watch_distance` o menos
        del jugador. El lado sale del signo de `direct × (p − jugador)`. Si empatan,
        decide `rng`."""
        left = right = 0
        for other in others:
            offset = other.position - player
            if offset.length() > self.spec.watch_distance:
                continue
            side = direct.cross(offset)
            left += side > 0
            right += side < 0
        if left == right:
            return rng.choice((-1, 1))
        return 1 if left < right else -1

    def _enter(self, state: ChargeState) -> None:
        self.state = state
        self._left = self._durations.get(state, 0)

    def _sees(self, enemy: Enemy, context: ActionContext) -> bool:
        """Si el jugador está a la vista y con la recta libre. Encima de él no hay
        dirección, y no avisa."""
        distance = enemy.position.distance_to(context.player_position)
        if distance == 0 or distance > self.spec.watch_distance:
            return False
        others = [other for other in context.enemies if other is not enemy]
        return clear_line(enemy.position, context.player_position, enemy.radius, others)


class VolleyState(Enum):
    WATCHING = auto()
    """Lo mueven sus patrones y gira con su `spin`. Espera al jugador a distancia."""
    TELEGRAPHING = auto()
    """Avisa: deja de girar, y sus puntas muestran hacia dónde van a salir las balas."""
    FIRING = auto()
    """Dispara una salva cada `interval`, girando con su `spin`."""
    RECOVERING = auto()
    """Lo mueven sus patrones y gira, pero todavía no puede avisar."""


class Volley(Action):
    """La ráfaga del pentágono: observa, avisa congelándose, dispara y se recupera.

    Solo avisa con el jugador entre `min_distance` y `max_distance`. Cada salva vuelve a
    mirar esa distancia: si el jugador quedó fuera, la ráfaga termina sin disparar. Cada
    salva es una bala por vértice, y como entre una y otra gira `ω·interval`, cada punta
    deja un brazo de la espiral de Arquímedes `r = (v/ω)·θ` (decisiones 31 a 33).
    """

    def __init__(self, spec: VolleySpec, cadence: float = 1.0) -> None:
        """Con `cadence` mayor que 1, se recupera antes: es el peligro del infinito. El
        aviso y la ráfaga no cambian."""
        self.spec = spec
        self.state = VolleyState.WATCHING
        self._interval = steps_of(spec.interval)
        self._durations = {
            VolleyState.TELEGRAPHING: steps_of(spec.telegraph),
            VolleyState.FIRING: spec.shots * self._interval,
            VolleyState.RECOVERING: steps_of(spec.cooldown / cadence),
        }
        self._left = 0
        """Los pasos que le quedan a la etapa, contando el actual."""

    @property
    def omega(self) -> float | None:
        return 0.0 if self.state is VolleyState.TELEGRAPHING else None

    def update(self, enemy: Enemy, context: ActionContext) -> list[Event]:
        if self.state is not VolleyState.WATCHING:
            self._left -= 1
            if self._left > 0:
                if self.state is VolleyState.FIRING and self._salvo_due():
                    if self._in_range(enemy, context):
                        self._fire(enemy, context)
                    else:
                        self._enter(VolleyState.RECOVERING)
                return []
            if self.state is VolleyState.TELEGRAPHING:
                if self._in_range(enemy, context):
                    self._enter(VolleyState.FIRING)
                    self._fire(enemy, context)
                    return []
                # A quemarropa o fuera de la vista al soltarse: no dispara.
                self._enter(VolleyState.WATCHING)
            elif self.state is VolleyState.FIRING:
                self._enter(VolleyState.RECOVERING)
                return []
            else:
                self._enter(VolleyState.WATCHING)
        # Al terminar la recuperación, ya mira en este mismo paso.
        if self.state is VolleyState.WATCHING and self._in_range(enemy, context):
            self._enter(VolleyState.TELEGRAPHING)
            return [Telegraph(enemy)]
        return []

    def _salvo_due(self) -> bool:
        """Si en este paso de la ráfaga toca una salva: una al entrar, y otra cada
        `interval` pasos."""
        elapsed = self._durations[VolleyState.FIRING] - self._left
        return elapsed % self._interval == 0

    def _fire(self, enemy: Enemy, context: ActionContext) -> None:
        """Una salva: una bala por cada vértice que le queda, desde el vértice y hacia
        afuera del centro de la figura."""
        shape = enemy.spec.shape
        # Un círculo con volley se rechaza al crear el mundo (`check_shapes`).
        assert isinstance(shape, StarPolygonShape)
        ends = line_vertices(shape)
        tips = sorted({k for e in enemy.edges for k in ends[e]})
        center = enemy.position + rotate(enemy.offset, enemy.angle)
        speed = context.bullet_spec.speed
        for k in tips:
            tip = rotate(vertex(enemy.spec.radius, shape.vertices, k), enemy.angle)
            context.bullets.append(EnemyBullet(center + tip, tip.normalize() * speed))

    def _in_range(self, enemy: Enemy, context: ActionContext) -> bool:
        distance = enemy.position.distance_to(context.player_position)
        return self.spec.min_distance <= distance <= self.spec.max_distance

    def _enter(self, state: VolleyState) -> None:
        self.state = state
        self._left = self._durations.get(state, 0)


class SpiralState(Enum):
    CROSSING = auto()
    """Va derecho a cruzar el centro de la masa crítica, atrayendo."""
    CARRYING = auto()
    """Lo cruzó: da media vuelta alrededor del jugador, llevándose a los que atrapó."""
    CIRCLING = auto()
    """Los soltó: te persigue en espiral, repeliendo."""


class Spiral(Action):
    """La espiral del círculo: cruza la masa crítica, se lleva a parte de ella al otro
    lado del jugador y después lo persigue en espiral, mirando solo dónde está
    (decisiones 53, 54 y 57).

    - **Cruzar:** va a `cross_speed` hacia el centroide de los que cuentan para la masa
      crítica, corrigiendo el rumbo. Cuando lo pasa, porque el centroide quedó detrás de
      su avance, empieza a cargar. Sin nadie que contar, gira desde el principio.
    - **Cargar:** da media vuelta alrededor del jugador a `carry_speed`, acercándose o
      alejándose hasta `carry_radius`. Mientras cruza y carga, su carga atrae: los que
      atrapa lo siguen. Al sumar `π` de giro, los suelta y empieza a girar.
    - **Girar:** en cada paso, el offset `d` desde el jugador gira `ω·dt` y se encoge por
      `e^(−λ·dt)`. Con el jugador quieto es la espiral logarítmica exacta, que corta
      cada radio en el mismo ángulo, `atan(ω/λ)`. Como solo mira las posiciones de este
      paso, no hereda la velocidad del jugador: si corre, queda atrás y lo persigue en
      curva. Su carga vuelve a repeler.

    Impone su velocidad sin tope, como la embestida.
    """

    def __init__(self, spec: SpiralSpec) -> None:
        self.spec = spec
        self.state = SpiralState.CROSSING
        self._velocity = Vector2()
        self._turned = 0.0
        """Cuánto giró alrededor del jugador al cargar, en radianes."""

    @property
    def controls_motion(self) -> bool:
        return True

    @property
    def velocity(self) -> Vector2:
        return self._velocity

    @property
    def charge_scale(self) -> float | None:
        """Atrae mientras cruza y carga; al girar, su carga es la de siempre."""
        return None if self.state is SpiralState.CIRCLING else -1.0

    def update(self, enemy: Enemy, context: ActionContext) -> list[Event]:
        """Fija la velocidad de este paso según la etapa."""
        if self.state is SpiralState.CROSSING:
            self._cross(enemy, context)
        if self.state is SpiralState.CARRYING:
            self._carry(enemy, context.player_position)
        elif self.state is SpiralState.CIRCLING:
            self._circle(enemy, context.player_position)
        return []

    def _cross(self, enemy: Enemy, context: ActionContext) -> None:
        """Rumbo al centroide de la masa crítica, o a cargar si ya lo pasó.

        También empieza a cargar al llegar a `carry_radius` del jugador: el centroide de
        las posiciones puede caer cerca de él, o al otro lado, aunque `Σû` apunte al
        grupo, y el cruce nunca pasa por encima del jugador (decisión 56)."""
        others = [
            e.position
            for e in context.enemies
            if e is not enemy and not e.spec.anchored
        ]
        if not others:
            self.state = SpiralState.CIRCLING
            return
        ahead = sum(others, Vector2()) / len(others) - enemy.position
        near = enemy.position.distance_to(context.player_position) <= (
            self.spec.carry_radius
        )
        if ahead.length_squared() == 0 or self._velocity.dot(ahead) < 0 or near:
            self.state = SpiralState.CARRYING
            return
        self._velocity = ahead.normalize() * self.spec.cross_speed

    def _carry(self, enemy: Enemy, player: Vector2) -> None:
        """Un paso de la media vuelta: el offset gira `carry_speed·dt / r` en el sentido
        de `ω`, y su largo se acerca a `carry_radius` a lo más `carry_speed·dt`."""
        offset = enemy.position - player
        r = offset.length()
        if r == 0:
            self.state = SpiralState.CIRCLING
            self._velocity = Vector2()
            return
        reach = self.spec.carry_speed * STEP
        turn = math.copysign(reach / r, self.spec.angular_speed)
        radius = r + max(-reach, min(reach, self.spec.carry_radius - r))
        target = player + offset.rotate_rad(turn) * (radius / r)
        self._velocity = (target - enemy.position) / STEP
        self._turned += abs(turn)
        if self._turned >= math.pi:
            self.state = SpiralState.CIRCLING

    def _circle(self, enemy: Enemy, player: Vector2) -> None:
        """La velocidad que lleva el offset `d` a `R(ω·dt)·d·e^(−λ·dt)` en un paso."""
        offset = enemy.position - player
        shrink = math.exp(-self.spec.decay * STEP)
        target = player + offset.rotate_rad(self.spec.angular_speed * STEP) * shrink
        self._velocity = (target - enemy.position) / STEP


class Regenerate(Action):
    """El médico: herido, recupera la línea que le falta de índice menor cada
    `interval`, una tasa constante de `1/interval` líneas por segundo. Entero, dona al
    herido más cercano a él su línea más cercana a ese herido, y la vuelve a recuperar
    con la misma cuenta: la línea se conserva al pasar de uno a otro (decisiones 65, 67
    y 69 de la spec de la 0.2.0).

    La cuenta parte de nuevo con cada golpe, cada línea recuperada y cada donación. Sabe
    que lo golpearon porque le quedan menos líneas que en su paso anterior: no necesita
    que el arma le avise. Entero y sin heridos, la cuenta queda cumplida, esperando.
    """

    def __init__(self, spec: RegenerateSpec) -> None:
        self.spec = spec
        self._interval = steps_of(spec.interval)
        self._left = self._interval
        """Los pasos que faltan para recuperar una línea, contando el actual."""
        self._seen: int | None = None
        """Cuántas líneas tenía al terminar su paso anterior."""

    def update(self, enemy: Enemy, context: ActionContext) -> list[Event]:
        if not enemy.alive:
            return []
        if self._seen is not None and len(enemy.edges) < self._seen:
            self._left = self._interval
        events: list[Event] = []
        self._left = max(0, self._left - 1)
        if self._left == 0:
            if enemy.wounded:
                missing = set(range(enemy.spec.shape.line_count)) - set(enemy.edges)
                k = min(missing)
                enemy.restore_edge(k, context.steps)
                events.append(Regrow(enemy, k))
                self._left = self._interval
            elif (patient := nearest_wounded(enemy, context.enemies)) is not None:
                events.append(self._donate(enemy, patient))
                self._left = self._interval
        # Después de donar: la línea que soltó no se lee como un golpe.
        self._seen = len(enemy.edges)
        return events

    @staticmethod
    def _donate(enemy: Enemy, patient: Enemy) -> Donate:
        """Suelta la línea cuyo punto medio queda más cerca de `patient`."""
        lines = dict(zip(enemy.edges, enemy.lines(), strict=True))

        def distance(k: int) -> float:
            a, b = lines[k]
            return ((a + b) / 2).distance_to(patient.position)

        k = min(lines, key=distance)
        enemy.remove_edge(k)
        return Donate(enemy, k, lines[k], patient)


def nearest_wounded(enemy: Enemy, others: Sequence[Enemy]) -> Enemy | None:
    """El herido más cercano a `enemy`, sin contarlo a él ni a las líneas sueltas, o
    `None`. Si empatan, el primero de la lista. Los fantasmas ya no vienen en `others`
    (`step_actions`)."""
    wounded = [e for e in others if e is not enemy and e.wounded and not e.stray]
    if not wounded:
        return None
    return min(wounded, key=lambda e: e.position.distance_to(enemy.position))


class Deliver(Action):
    """La línea suelta: va a `speed` hacia su paciente mientras siga herido. Si muere o
    queda entero, lo suelta, y desde ahí la mueven sus patrones y su roce: frena y queda
    flotando (decisión 68 de la spec de la 0.2.0). No busca otro."""

    def __init__(self, spec: DeliverSpec) -> None:
        self.spec = spec
        self.patient: Enemy | None = None
        """El herido al que va. Lo fija el mundo al soltarla."""
        self.donor: Enemy | None = None
        """El médico que la soltó. Mientras va a su paciente, él no la absorbe."""
        self._velocity: Vector2 | None = None

    @property
    def controls_motion(self) -> bool:
        return self._velocity is not None

    @property
    def velocity(self) -> Vector2 | None:
        return self._velocity

    def update(self, enemy: Enemy, context: ActionContext) -> list[Event]:
        if self.patient is not None and not self.patient.wounded:
            self.patient = None
        if self.patient is None:
            self._velocity = None
            return []
        ahead = self.patient.position - enemy.position
        if ahead.length_squared() == 0:
            self._velocity = Vector2()
        else:
            self._velocity = ahead.normalize() * self.spec.speed
        return []


def check_actions(enemies: Mapping[str, EnemySpec]) -> None:
    """Rechaza al crear el mundo una espiral que no se acerca (`decay ≤ 0`), que no
    gira (`angular_speed = 0`), que no cruza (`cross_speed ≤ 0`) o que no carga
    (`carry_speed ≤ 0` o `carry_radius ≤ 0`), nombrando a su enemigo."""
    for name, spec in enemies.items():
        for action in spec.actions:
            if isinstance(action, RegenerateSpec):
                check_stray(name, action, enemies)
            if isinstance(action, SpiralSpec) and (
                action.decay <= 0
                or action.angular_speed == 0
                or action.cross_speed <= 0
                or action.carry_speed <= 0
                or action.carry_radius <= 0
            ):
                raise ValueError(
                    f"enemies.{name}.actions: una espiral necesita decay > 0,"
                    " angular_speed ≠ 0, y cross_speed, carry_speed y carry_radius"
                    f" > 0, no {action}"
                )


def check_stray(
    name: str, action: RegenerateSpec, enemies: Mapping[str, EnemySpec]
) -> None:
    """Rechaza un médico cuyo `stray` no existe, o no es un segmento con `deliver`."""
    stray = enemies.get(action.stray)
    if (
        stray is None
        or not isinstance(stray.shape, SegmentShape)
        or not any(isinstance(a, DeliverSpec) for a in stray.actions)
    ):
        raise ValueError(
            f"enemies.{name}.actions: el stray {action.stray!r} tiene que ser un"
            " enemigo con figura de segmento y la acción deliver"
        )


def make_action(spec: ActionSpec, cadence: float = 1.0) -> Action:
    """La instancia de la acción que describe `spec`, nueva para cada enemigo. La
    `cadence` del peligro solo cambia a los ataques: la embestida y la ráfaga."""
    match spec:
        case ChargeSpec():
            return Charge(spec, cadence)
        case VolleySpec():
            return Volley(spec, cadence)
        case SpiralSpec():
            return Spiral(spec)
        case RegenerateSpec():
            return Regenerate(spec)
        case DeliverSpec():
            return Deliver(spec)


def step_actions(
    enemies: Sequence[Enemy],
    player_position: Vector2,
    rng: random.Random,
    bullets: list[EnemyBullet],
    bullet_spec: EnemyBulletSpec,
    steps: int = 0,
) -> list[Event]:
    """Avanza un paso las acciones de todos los enemigos vivos, y devuelve sus eventos.
    Las balas que disparen quedan en `bullets`, y `steps` es el paso del mundo.

    Van en el orden de la lista, que es el de aparición: así, lo que sacan de `rng` es
    siempre lo mismo con la misma semilla.

    Los fantasmas no cuentan: los demás los atraviesan, así que no tapan una recta."""
    alive = [enemy for enemy in enemies if enemy.alive and not enemy.spec.phantom]
    context = ActionContext(
        Vector2(player_position), alive, rng, bullets, bullet_spec, steps
    )
    events: list[Event] = []
    for enemy in alive:
        for action in enemy.actions:
            events += action.update(enemy, context)
    return events
