"""Las armas: disparan solas desde el jugador.

Toda arma hereda de `Weapon` y avanza con `update`, un paso de `STEP` a la vez (ADR 0005).
Cada arma lee su `spec` en cada paso, así que mejorarla es reemplazar su `spec`. Dónde
está lo que dispara sale de sus términos, en `world/terms.py` (ADR 0029).
"""

import math
from abc import ABC, abstractmethod

from pygame.math import Vector2

from circlebh.balance import Balance, WeaponSpec
from circlebh.world.clock import STEP
from circlebh.world.enemy import Enemy
from circlebh.world.events import Event, Hit, Shot
from circlebh.world.terms import advance_at, projectile_offset


class Weapon(ABC):
    """La base de toda arma."""

    def __init__(self, spec: WeaponSpec) -> None:
        self.spec = spec

    @abstractmethod
    def update(self, origin: Vector2, enemies: list[Enemy]) -> list[Event]:
        """Avanza un paso. `origin` es la posición del jugador en este paso, y `enemies`,
        los enemigos vivos. Devuelve los eventos del paso: disparos y golpes."""


def check_weapons(balance: Balance) -> None:
    """Rechaza al crear el mundo un arma que el código todavía no sabe armar, nombrando
    el campo, para que un dato del balance no quede ignorado en silencio.

    Lo que se rechaza aquí llega con su tarea del plan de la 0.3.0: los trazos, el marco
    polar, apuntar hacia donde te mueves, `d/dt` y `∫dt`, los operadores y lo que viaja.
    """
    start = balance.player.start_weapon
    if start not in balance.weapons:
        raise ValueError(f"player.start_weapon: no existe el arma {start}")
    for name, spec in balance.weapons.items():
        unsupported = {
            "kind": spec.kind != "projectile",
            "frame": spec.frame != "cartesian",
            "aim": spec.aim != "nearest",
            "advance.degree": spec.advance.degree != 1,
            "copies": spec.copies != 1,
            "mirror": spec.mirror,
            "parallel": spec.parallel != 0,
            "payload.size": spec.payload.size != 0,
            "payload.lines": spec.payload.lines != 1,
            "payload.pierce": spec.payload.pierce != 0,
        }
        for field, rejected in unsupported.items():
            if rejected:
                raise ValueError(
                    f"weapons.{name}.{field}: el código todavía no sabe armarlo"
                )


class Bullet:
    """Un proyectil: sigue los términos de su arma desde donde nació, `p(t) = p₀ +
    x(t)·û + y(t)·n̂`, y desaparece cuando su avance llega a `reach`.

    `(x(t), y(t))` es `projectile_offset`, en el marco local, y `n̂` es `û` girado un
    cuarto de vuelta antihorario. No persigue: su `û` queda fijo al nacer.
    """

    def __init__(self, origin: Vector2, direction: Vector2, spec: WeaponSpec) -> None:
        # Copias: `Player.position` cambia en el lugar, y la bala no debe seguirlo.
        self.origin = Vector2(origin)
        self.direction = Vector2(direction)
        """`û`, de largo 1: hacia dónde se disparó."""
        self.spec = spec
        """El `spec` del arma cuando nació. Una mejora posterior no lo cambia."""
        self._steps = 0

    @property
    def age(self) -> float:
        """Segundos desde que nació, contados en pasos enteros como `World.elapsed`."""
        return self._steps * STEP

    def _at(self, t: float) -> Vector2:
        """`p(t) = p₀ + x(t)·û + y(t)·n̂`."""
        offset = projectile_offset(self.spec, t)
        normal = Vector2(-self.direction.y, self.direction.x)
        return self.origin + self.direction * offset.x + normal * offset.y

    @property
    def position(self) -> Vector2:
        """Dónde está ahora."""
        return self._at(self.age)

    @property
    def previous(self) -> Vector2:
        """Dónde estaba un paso antes. Al nacer, en `origin`."""
        return self._at(max(0, self._steps - 1) * STEP)

    @property
    def expired(self) -> bool:
        """Desaparece cuando su avance llega a `reach`."""
        return advance_at(self.spec, self.age) >= self.spec.reach

    def step(self) -> None:
        """Avanza un paso."""
        self._steps += 1


def intercept(
    origin: Vector2, target: Vector2, velocity: Vector2, speed: float
) -> Vector2:
    """Hacia dónde disparar desde `origin` una bala de rapidez `speed` para que se cruce
    con un objetivo en `target` que sigue derecho a `velocity` (decisión 55).

    El cruce, en el tiempo `t`, cumple `|d + v·t| = s·t`, con `d = target − origin`. Al
    cuadrado queda `(v·v − s²)·t² + 2(d·v)·t + d·d = 0`, y se toma la menor raíz
    positiva. Si no hay ninguna, porque el objetivo se aleja más rápido que la bala,
    apunta a donde está, como un arma sin anticipación.
    """
    d = target - origin
    a = velocity.dot(velocity) - speed * speed
    b = d.dot(velocity)
    c = d.dot(d)
    if a == 0:
        # Igual de rápidos: la ecuación es lineal, `2b·t + c = 0`.
        times = [-c / (2 * b)] if b < 0 else []
    else:
        discriminant = b * b - a * c
        if discriminant < 0:
            return Vector2(target)
        root = math.sqrt(discriminant)
        times = [t for t in ((-b - root) / a, (-b + root) / a) if t > 0]
    if not times:
        return Vector2(target)
    return target + velocity * min(times)


def nearest(origin: Vector2, enemies: list[Enemy]) -> Enemy | None:
    """El enemigo de centro más cercano a `origin` al que se puede apuntar. Si empatan,
    el primero de la lista.

    Descarta a los muertos (los que perdieron su última línea en este paso y `World`
    todavía no quita) y a los que tienen el centro en `origin`: hacia ellos no hay
    dirección. Un enemigo abierto puede quedar estacionado sobre el jugador quieto; así
    no calla el arma contra los demás, y para pegarle hay que moverse (decisión 18).

    Tampoco apunta a los fantasmas, como la gran estrella roja: el arma sigue apuntando
    al enjambre, y sus balas rompen las líneas rojas que hay en el camino (decisión 44).

    Se compara la distancia al cuadrado con 0 y no `position != origin`, porque la
    igualdad de `Vector2` tiene una tolerancia de 1e-6. La distancia al cuadrado es el
    largo al cuadrado de la dirección del disparo: si no es 0, se puede normalizar.
    """
    targets = [
        e
        for e in enemies
        if e.alive and not e.spec.phantom and e.position.distance_squared_to(origin) > 0
    ]
    # `min` devuelve el primero de los empatados.
    return min(
        targets,
        key=lambda enemy: enemy.position.distance_squared_to(origin),
        default=None,
    )


class ProjectileWeapon(Weapon):
    """Un arma de proyectiles: uno cada `cooldown` segundos hacia el enemigo más
    cercano, que sigue los términos de su `spec`."""

    def __init__(self, spec: WeaponSpec) -> None:
        super().__init__(spec)
        self.bullets: list[Bullet] = []
        self._steps_to_next = 0
        """Pasos que faltan para el próximo disparo. Parte en 0: dispara en el primer
        paso en que tenga a quién."""

    def update(self, origin: Vector2, enemies: list[Enemy]) -> list[Event]:
        """Avanza las balas, aplica sus golpes, quita las gastadas y, si toca, dispara
        desde `origin`.

        Cada bala quita una sola línea y desaparece. Si su tramo cruza líneas de dos
        enemigos, golpea la primera que cruza; si empatan, la del primero de la lista.
        Una bala que llega a `reach` en este paso todavía golpea con su último tramo.

        La bala nueva nace en `origin` y empieza a moverse en el paso siguiente. Sin
        objetivo, o con su centro justo en `origin`, no dispara y queda lista.

        Devuelve un `Hit` por cada línea quitada y un `Shot` si disparó.
        """
        events: list[Event] = []
        remaining: list[Bullet] = []
        for bullet in self.bullets:
            bullet.step()
            hit = self._strike(bullet, enemies)
            if hit is not None:
                events.append(hit)
            elif not bullet.expired:
                remaining.append(bullet)
        self.bullets = remaining
        self._steps_to_next -= 1
        if self._steps_to_next <= 0 and self._fire(origin, enemies):
            events.append(Shot(self))
        return events

    @staticmethod
    def _strike(bullet: Bullet, enemies: list[Enemy]) -> Hit | None:
        """Si el último tramo de `bullet` cruza una línea, la quita y devuelve el golpe."""
        best: tuple[float, int, Enemy, int] | None = None
        for index, enemy in enumerate(enemies):
            crossing = enemy.hit_by(bullet.previous, bullet.position)
            if crossing is not None and (best is None or crossing[0] < best[0]):
                t, k = crossing
                best = (t, index, enemy, k)
        if best is None:
            return None
        _, _, enemy, k = best
        enemy.remove_edge(k)
        return Hit(enemy, k)

    def _fire(self, origin: Vector2, enemies: list[Enemy]) -> bool:
        """Dispara al más cercano, hacia donde se va a cruzar con la bala, y devuelve
        `True`. Sin objetivo, no dispara."""
        target = nearest(origin, enemies)
        if target is None:
            return False
        # El punto avanza con grado 1: su rapidez es el coeficiente del avance.
        speed = self.spec.advance.coefficient
        aim = intercept(origin, target.position, target.velocity, speed)
        if aim.distance_squared_to(origin) == 0:
            # `nearest` garantiza que el objetivo mismo da una dirección.
            aim = target.position
        direction = (aim - origin).normalize()
        self.bullets.append(Bullet(origin, direction, self.spec))
        self._steps_to_next = round(self.spec.cooldown / STEP)
        return True
