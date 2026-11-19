"""Las armas: curvas que disparan solas alrededor del jugador.

Toda arma hereda de `Weapon` y avanza con `update`, un paso de `STEP` a la vez (ADR 0005).
Cada arma lee su `spec` en cada paso, así que mejorarla es reemplazar su `spec`.
"""

from abc import ABC, abstractmethod

from pygame.math import Vector2

from circlebh.balance import CircleWeaponSpec
from circlebh.world.clock import STEP


class Weapon(ABC):
    """La base de toda arma."""

    @abstractmethod
    def update(self, origin: Vector2) -> None:
        """Avanza un paso. `origin` es la posición del jugador en este paso."""


class Ring:
    """Un anillo del arma círculo: crece con `r(t) = growth_speed · t` y revienta en
    `max_radius`.

    Su centro queda fijo donde nació: es un proyectil que se expande, no un aura que
    sigue al jugador.
    """

    def __init__(self, center: Vector2, spec: CircleWeaponSpec) -> None:
        # Una copia: `Player.position` cambia en el lugar, y el anillo no debe seguirlo.
        self.center = Vector2(center)
        self.spec = spec
        """El `spec` del arma cuando nació. Una mejora posterior no lo cambia."""
        self._steps = 0

    @property
    def age(self) -> float:
        """Segundos desde que nació, contados en pasos enteros como `World.elapsed`."""
        return self._steps * STEP

    @property
    def radius(self) -> float:
        """`r(t) = growth_speed · t`."""
        return self.spec.growth_speed * self.age

    @property
    def expired(self) -> bool:
        """Revienta al llegar a `max_radius`."""
        return self.radius >= self.spec.max_radius

    def step(self) -> None:
        """Envejece un paso."""
        self._steps += 1


class CircleWeapon(Weapon):
    """El arma círculo: un anillo nuevo en el jugador cada `cooldown` segundos."""

    def __init__(self, spec: CircleWeaponSpec) -> None:
        self.spec = spec
        self.rings: list[Ring] = []
        self._steps_to_next = 0
        """Pasos que faltan para el próximo anillo. Parte en 0: el primero nace en el
        primer paso."""

    def update(self, origin: Vector2) -> None:
        """Envejece los anillos, quita los reventados y, si toca, lanza uno en `origin`.

        El anillo nuevo nace con radio 0 y empieza a crecer en el paso siguiente.
        """
        for ring in self.rings:
            ring.step()
        self.rings = [ring for ring in self.rings if not ring.expired]
        if self._steps_to_next <= 0:
            self.rings.append(Ring(origin, self.spec))
            self._steps_to_next = round(self.spec.cooldown / STEP)
        self._steps_to_next -= 1
