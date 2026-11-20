"""Las armas: disparan solas desde el jugador.

Toda arma hereda de `Weapon` y avanza con `update`, un paso de `STEP` a la vez (ADR 0005).
Cada arma lee su `spec` en cada paso, así que mejorarla es reemplazar su `spec`.
"""

from abc import ABC, abstractmethod

from pygame.math import Vector2

from circlebh.balance import PointWeaponSpec
from circlebh.world.clock import STEP
from circlebh.world.enemy import Enemy


class Weapon(ABC):
    """La base de toda arma."""

    @abstractmethod
    def update(self, origin: Vector2, enemies: list[Enemy]) -> None:
        """Avanza un paso. `origin` es la posición del jugador en este paso, y `enemies`,
        los enemigos vivos."""


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


def nearest(origin: Vector2, enemies: list[Enemy]) -> Enemy | None:
    """El enemigo de centro más cercano a `origin`. Si empatan, el primero de la lista."""
    # `min` devuelve el primero de los empatados.
    return min(
        enemies,
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

    def update(self, origin: Vector2, enemies: list[Enemy]) -> None:
        """Avanza las balas, quita las vencidas y, si toca, dispara desde `origin`.

        La bala nueva nace en `origin` y empieza a moverse en el paso siguiente. Sin
        objetivo, o con su centro justo en `origin`, no dispara y queda lista.
        """
        for bullet in self.bullets:
            bullet.step()
        self.bullets = [bullet for bullet in self.bullets if not bullet.expired]
        self._steps_to_next -= 1
        if self._steps_to_next <= 0:
            self._fire(origin, enemies)

    def _fire(self, origin: Vector2, enemies: list[Enemy]) -> None:
        target = nearest(origin, enemies)
        if target is None:
            return
        direction = target.position - origin
        # Dirección nula: no se puede normalizar.
        if direction.length_squared() == 0:
            return
        velocity = direction.normalize() * self.spec.speed
        self.bullets.append(Bullet(origin, velocity, self.spec))
        self._steps_to_next = round(self.spec.cooldown / STEP)
