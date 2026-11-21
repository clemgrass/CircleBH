"""Los enemigos: polígonos regulares hechos de líneas, que se mueven por sus patrones, con
inercia y roce (ADR 0021).

Cada línea es una parte del enemigo: la bala quita la que golpea, y sin líneas el enemigo
muere. Chocan por sus líneas, y el círculo envolvente es el primer descarte (ADR 0020).
"""

from pygame.math import Vector2

from circlebh.balance import EnemySpec
from circlebh.world.clock import STEP
from circlebh.world.collisions import circles_touch, segment_touches_circle
from circlebh.world.patterns import Context, make_pattern
from circlebh.world.polygon import (
    ENVELOPE_SLACK,
    edge_sectors,
    first_hit,
    polygon_edge,
)


class Enemy:
    """Un enemigo, en coordenadas del plano."""

    def __init__(self, spec: EnemySpec, position: Vector2) -> None:
        self.spec = spec
        self.position = Vector2(position)
        self.previous = Vector2(position)
        """Dónde estaba antes del último `step`. Lo usa el tramo relativo de `hit_by`."""
        self.edges = list(range(spec.sides))
        """Las aristas que le quedan, de menor a mayor (ver `polygon.py`)."""
        self.velocity = Vector2()
        """Unidades del plano por segundo. Parte quieto."""
        self.patterns = [make_pattern(pattern) for pattern in spec.patterns]
        """Su conducta: instancias propias de los patrones de su tipo (ADR 0021)."""

    @property
    def mass(self) -> float:
        """Las líneas que le quedan (ADR 0021)."""
        return float(len(self.edges))

    @property
    def charge(self) -> float:
        """`charge_per_line` por las líneas que le quedan. Como la masa también son sus
        líneas, un herido empuja menos, y a él lo empujan igual."""
        return self.spec.charge_per_line * len(self.edges)

    @property
    def radius(self) -> float:
        """Radio del círculo envolvente: el del polígono completo. No es un hitbox: las
        líneas que quedan no se mueven, así que no se achica."""
        return self.spec.radius

    @property
    def alive(self) -> bool:
        """Vive mientras le quede alguna línea."""
        return bool(self.edges)

    def remove_edge(self, k: int) -> None:
        """Quita la arista `k`: una bala la golpeó."""
        self.edges.remove(k)

    def lines(self) -> list[tuple[Vector2, Vector2]]:
        """Las líneas que le quedan, en coordenadas del plano."""
        return [
            (self.position + a, self.position + b)
            for a, b in (
                polygon_edge(self.spec.radius, self.spec.sides, k) for k in self.edges
            )
        ]

    def touches(self, center: Vector2, radius: float) -> bool:
        """Si alguna de sus líneas toca al círculo de `center` y `radius`.

        Primero descarta con el círculo envolvente; solo si lo toca, prueba cada línea.
        Un círculo dentro del enemigo que no toca ninguna línea no lo toca.
        """
        if not circles_touch(
            center, radius, self.position, self.radius + ENVELOPE_SLACK
        ):
            return False
        return any(
            segment_touches_circle(a, b, center, radius) for a, b in self.lines()
        )

    def hit_by(self, start: Vector2, end: Vector2) -> tuple[float, int] | None:
        """La primera línea que cruza el tramo de una bala en el último paso, como `(t, k)`.

        `start` y `end` son dónde estaba la bala antes y después del paso. El tramo se
        mide desde el enemigo, que también se movió: de `start − previous` a
        `end − position`. Como el enemigo solo se traslada, ese tramo relativo es exacto, y
        un enemigo que avanza hacia la bala no la deja pasar entre dos pasos.
        """
        relative_start = start - self.previous
        relative_end = end - self.position
        if not segment_touches_circle(
            relative_start, relative_end, Vector2(), self.radius + ENVELOPE_SLACK
        ):
            return None
        sides = self.spec.sides
        candidates = [
            k
            for k in edge_sectors(relative_start, relative_end, sides)
            if k in self.edges
        ]
        return first_hit(relative_start, relative_end, self.radius, sides, candidates)

    def acceleration(self, context: Context) -> Vector2:
        """La suma de lo que aporta cada patrón, menos el roce: `a = Σ patrón − γ·v`."""
        total = -self.velocity * self.spec.friction
        for pattern in self.patterns:
            total += pattern.acceleration(self, context)
        return total

    def step(self, acceleration: Vector2) -> None:
        """Avanza un paso con Euler semi-implícito: primero la velocidad, después la
        posición con la velocidad nueva.

        `v ← v + a·dt`, acotada a `speed`, y `p ← p + v·dt`. Es estable con roce, y el tope
        hace que nadie avance más de `speed·dt` por paso, aunque una fuerza sea enorme.
        """
        self.previous = Vector2(self.position)
        self.velocity = (self.velocity + acceleration * STEP).clamp_magnitude(
            self.spec.speed
        )
        self.position = self.position + self.velocity * STEP
