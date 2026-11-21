"""Los enemigos: polígonos regulares hechos de líneas, que se mueven por sus patrones, con
inercia y roce (ADR 0021), y algunos giran (ADR 0027). Algunos tienen acciones, como la
embestida, que pueden apagar sus patrones (`world/actions.py`).

Cada línea es una parte del enemigo: la bala quita la que golpea, y sin líneas el enemigo
muere. Chocan por sus líneas, y el círculo envolvente es el primer descarte (ADR 0020).
"""

from pygame.math import Vector2

from circlebh.balance import EnemySpec
from circlebh.world.actions import make_action
from circlebh.world.clock import STEP
from circlebh.world.collisions import circles_touch, segment_touches_circle
from circlebh.world.patterns import Context, make_pattern
from circlebh.world.polygon import (
    ENVELOPE_SLACK,
    edge_sectors,
    first_hit,
    polygon_edge,
)
from circlebh.world.rigid import center_of_mass, rotate, to_local, to_world


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
        self.angle = 0.0
        """Su orientación `θ`, en radianes y antihoraria. Todos parten en 0."""
        self.previous_angle = 0.0
        """Su orientación antes del último `step`. La usa `hit_by`, como `previous`."""
        self.omega = spec.spin
        """Su velocidad angular `ω`, en rad/s. Parte en `spec.spin` y no cambia."""
        self.offset = Vector2()
        """Dónde queda el centro del polígono visto desde `position`, en el marco del
        enemigo. Parte en 0. Si gira y pierde una línea, `position` pasa a su nuevo
        centro de masa, y esto guarda cuánto se corrió (ADR 0027)."""
        self._radius = spec.radius
        self.patterns = [make_pattern(pattern) for pattern in spec.patterns]
        """Su conducta: instancias propias de los patrones de su tipo (ADR 0021)."""
        self.actions = [make_action(action) for action in spec.actions]
        """Sus acciones, con su propio estado: lo que hace y no es una fuerza."""

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
        """Radio del círculo envolvente, en torno a `position`. No es un hitbox.

        Sin giro, es el del polígono completo y no se achica: las líneas que quedan no
        se mueven. Con giro, al perder una línea, es la distancia del centro de masa
        nuevo al extremo más lejano de las que quedan."""
        return self._radius

    @property
    def alive(self) -> bool:
        """Vive mientras le quede alguna línea."""
        return bool(self.edges)

    def remove_edge(self, k: int) -> None:
        """Quita la arista `k`: una bala la golpeó.

        Sin giro, nada más cambia (spec de la 0.1.0, decisión 15). Con giro, el resto
        sigue con el mismo `ω`, como un cuerpo que se rompe, y gira en torno a su nuevo
        centro de masa `c'` (L2 del ADR 0027):

        - `position` pasa a `c'`, y `previous` se corre igual, con la pose de antes.
          Así las líneas no se mueven en el plano, ni en la pose de antes del paso.
        - `velocity` pasa a la que tenía ese punto: `v + ω × (c' − c)`.
        """
        self.edges.remove(k)
        if self.spec.spin == 0 or not self.edges:
            return
        # `shift` es `c' − c` en el marco del enemigo, y `moved`, en el plano.
        shift = center_of_mass(self._local_lines())
        moved = rotate(shift, self.angle)
        self.offset -= shift
        self.position += moved
        self.previous += rotate(shift, self.previous_angle)
        self.velocity += self.omega * Vector2(-moved.y, moved.x)
        self._radius = max(p.length() for line in self._local_lines() for p in line)

    def _local_lines(self) -> list[tuple[Vector2, Vector2]]:
        """Las líneas que le quedan, en el marco del enemigo: desde `position`, sin
        girar."""
        return [
            (a + self.offset, b + self.offset)
            for a, b in (
                polygon_edge(self.spec.radius, self.spec.sides, k) for k in self.edges
            )
        ]

    def lines(self) -> list[tuple[Vector2, Vector2]]:
        """Las líneas que le quedan, en coordenadas del plano, giradas en `angle`."""
        return [
            (
                to_world(a, self.position, self.angle),
                to_world(b, self.position, self.angle),
            )
            for a, b in self._local_lines()
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
        mide en el marco del enemigo, que también se movió: `start` con la pose de antes
        y `end` con la de ahora, `R(−θ)·(p − c)`. Así un enemigo que avanza hacia la
        bala no la deja pasar entre dos pasos.

        Sin giro, ese tramo es exacto. Con giro, el camino de la bala en el marco del
        enemigo es una curva, y el tramo recto entre sus extremos se aparta de ella a lo
        más `(2·|ω·dt|·|Δr| + (ω·dt)²·|r|) / 8` (ADR 0027).
        """
        # Del marco del enemigo, centrado en `position`, al del polígono, donde valen
        # los sectores (ADR 0020).
        relative_start = (
            to_local(start, self.previous, self.previous_angle) - self.offset
        )
        relative_end = to_local(end, self.position, self.angle) - self.offset
        if not segment_touches_circle(
            relative_start, relative_end, Vector2(), self.spec.radius + ENVELOPE_SLACK
        ):
            return None
        sides = self.spec.sides
        candidates = [
            k
            for k in edge_sectors(relative_start, relative_end, sides)
            if k in self.edges
        ]
        return first_hit(
            relative_start, relative_end, self.spec.radius, sides, candidates
        )

    def acceleration(self, context: Context) -> Vector2:
        """La suma de lo que aporta cada patrón, menos el roce: `a = Σ patrón − γ·v`.

        Si una acción apaga los patrones, queda solo el roce."""
        total = -self.velocity * self.spec.friction
        if any(action.controls_motion for action in self.actions):
            return total
        for pattern in self.patterns:
            total += pattern.acceleration(self, context)
        return total

    def step(self, acceleration: Vector2) -> None:
        """Avanza un paso con Euler semi-implícito: primero la velocidad, después la
        posición con la velocidad nueva.

        `v ← v + a·dt`, acotada a `speed`, y `p ← p + v·dt`. Es estable con roce, y el tope
        hace que nadie avance más de `speed·dt` por paso, aunque una fuerza sea enorme.
        El giro avanza igual: `θ ← θ + ω·dt`.

        Si una acción fija la velocidad, como la embestida, `v` es esa, sin tope. Si fija
        el giro, como el triángulo que te mira, `ω` es ese en este paso.
        """
        self.previous = Vector2(self.position)
        self.previous_angle = self.angle
        turn = next((a.omega for a in self.actions if a.omega is not None), self.omega)
        self.angle += turn * STEP
        imposed = next(
            (a.velocity for a in self.actions if a.velocity is not None), None
        )
        if imposed is not None:
            self.velocity = Vector2(imposed)
        else:
            self.velocity = (self.velocity + acceleration * STEP).clamp_magnitude(
                self.spec.speed
            )
        self.position = self.position + self.velocity * STEP
