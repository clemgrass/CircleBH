"""Las armas: disparan solas desde el jugador.

Toda arma hereda de `Weapon` y avanza con `update`, un paso de `STEP` a la vez (ADR 0005).
Cada arma lee su `spec` en cada paso, así que mejorarla es reemplazar su `spec`.
"""

import math
from abc import ABC, abstractmethod

from pygame.math import Vector2

from circlebh.balance import PointWeaponSpec
from circlebh.world.clock import STEP
from circlebh.world.enemy import Enemy
from circlebh.world.events import Event, Hit, Shot


class Weapon(ABC):
    """La base de toda arma."""

    @abstractmethod
    def update(self, origin: Vector2, enemies: list[Enemy]) -> list[Event]:
        """Avanza un paso. `origin` es la posición del jugador en este paso, y `enemies`,
        los enemigos vivos. Devuelve los eventos del paso: disparos y golpes."""


class Bullet:
    """Una bala del arma punto: avanza en línea recta, `p(t) = p₀ + v·t`, y desaparece
    al recorrer `range`.

    No persigue: su dirección queda fija al nacer.
    """

    def __init__(
        self, origin: Vector2, velocity: Vector2, spec: PointWeaponSpec
    ) -> None:
        # Copias: `Player.position` cambia en el lugar, y la bala no debe seguirlo.
        self.origin = Vector2(origin)
        self.velocity = Vector2(velocity)
        """Unidades del plano por segundo."""
        self.spec = spec
        """El `spec` del arma cuando nació. Una mejora posterior no lo cambia."""
        self._steps = 0

    @property
    def age(self) -> float:
        """Segundos desde que nació, contados en pasos enteros como `World.elapsed`."""
        return self._steps * STEP

    @property
    def position(self) -> Vector2:
        """`p(t) = p₀ + v·t`."""
        return self.origin + self.velocity * self.age

    @property
    def previous(self) -> Vector2:
        """Dónde estaba un paso antes. Al nacer, en `origin`."""
        return self.origin + self.velocity * max(0, self._steps - 1) * STEP

    @property
    def expired(self) -> bool:
        """Desaparece al recorrer `range`."""
        return self.spec.speed * self.age >= self.spec.range

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


class PointWeapon(Weapon):
    """El arma punto: una bala cada `cooldown` segundos hacia el enemigo más cercano."""

    def __init__(self, spec: PointWeaponSpec) -> None:
        self.spec = spec
        self.bullets: list[Bullet] = []
        self._steps_to_next = 0
        """Pasos que faltan para el próximo disparo. Parte en 0: dispara en el primer
        paso en que tenga a quién."""

    def update(self, origin: Vector2, enemies: list[Enemy]) -> list[Event]:
        """Avanza las balas, aplica sus golpes, quita las gastadas y, si toca, dispara
        desde `origin`.

        Cada bala quita una sola línea y desaparece. Si su tramo cruza líneas de dos
        enemigos, golpea la primera que cruza; si empatan, la del primero de la lista.
        Una bala que llega a `range` en este paso todavía golpea con su último tramo.

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
        aim = intercept(origin, target.position, target.velocity, self.spec.speed)
        if aim.distance_squared_to(origin) == 0:
            # `nearest` garantiza que el objetivo mismo da una dirección.
            aim = target.position
        velocity = (aim - origin).normalize() * self.spec.speed
        self.bullets.append(Bullet(origin, velocity, self.spec))
        self._steps_to_next = round(self.spec.cooldown / STEP)
        return True
