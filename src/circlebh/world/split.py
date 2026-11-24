"""El divisor: al morir, se parte en fragmentos (spec de la 0.2.0, "El divisor (#63)").

Un polígono convexo de `n` lados se triangula en abanico en `n − 2` triángulos, y en el
centroide de cada uno nace un enemigo del tipo `split_into` (decisión 71).
"""

from collections.abc import Mapping

from pygame.math import Vector2

from circlebh.balance import EnemySpec
from circlebh.world.collisions import circles_touch
from circlebh.world.enemy import Enemy
from circlebh.world.figures import is_regular, triangulation_centroids
from circlebh.world.rigid import to_world


def fragments(
    parent: Enemy, spec: EnemySpec, player: Vector2, player_radius: float
) -> list[Enemy]:
    """Los enemigos `spec` que suelta `parent` al morir, uno por triángulo de su
    triangulación.

    Cada centroide pasa al plano con la pose del padre: el centro de su figura, que con
    giro está corrido en `offset` desde `position`, y su ángulo. El fragmento nace con
    el ángulo y la velocidad del padre. Si su círculo envolvente tocaría al jugador, no
    nace: el jugador pudo meterse por un hueco del padre herido (Foco 3 del plan)."""
    shape = parent.spec.shape
    # `check_splits` ya rechazó al crear el mundo un padre que no es `{n/1}`.
    assert is_regular(shape)
    children: list[Enemy] = []
    for centroid in triangulation_centroids(shape, parent.spec.radius):
        position = to_world(centroid + parent.offset, parent.position, parent.angle)
        if circles_touch(position, spec.radius, player, player_radius):
            continue
        child = Enemy(spec, position)
        child.angle = child.previous_angle = parent.angle
        child.velocity = Vector2(parent.velocity)
        children.append(child)
    return children


def check_splits(enemies: Mapping[str, EnemySpec]) -> None:
    """Rechaza al crear el mundo, nombrando al enemigo, un `split_into` que no existe,
    uno en un padre que no es un polígono regular `{n/1}` (el abanico de una estrella o
    de un círculo no triangula su figura) y una cadena que vuelve sobre sí misma, que
    nunca terminaría de partirse."""
    for name, spec in enemies.items():
        into = spec.split_into
        if not into:
            continue
        where = f"enemies.{name}.split_into"
        if into not in enemies:
            raise ValueError(f"{where}: no existe el enemigo {into!r}")
        if not is_regular(spec.shape):
            raise ValueError(
                f"{where}: solo se parte un polígono regular {{n/1}}, y su figura no"
                " lo es"
            )
    for name in enemies:
        chain = [name]
        while into := enemies[chain[-1]].split_into:
            if into in chain:
                path = " → ".join([*chain, into])
                raise ValueError(
                    f"enemies.{name}.split_into: la cadena {path} forma un ciclo"
                )
            chain.append(into)
