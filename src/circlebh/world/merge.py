"""La fusión: cinco estrellas vivas se juntan en la gran estrella roja (spec de la 0.2.0,
decisiones 37 a 41).

La gran estrella aparece centrada en el jugador, así que el jugador queda dentro de la
figura. Para que nunca aparezca tocándolo, su línea más cercana al centro tiene que
quedar más lejos que el radio del jugador. En `{n/s}`, la línea de salto `s` es una
cuerda que abarca el ángulo `2πs/n`, y su distancia al centro es `R·cos(πs/n)`: la más
cercana es la del mayor `s`.
"""

import math

from circlebh.balance import Balance


def check_merge(balance: Balance) -> None:
    """Rechaza al crear el mundo una fusión con tipos que no existen, o cuya figura
    tocaría al jugador al aparecer centrada en él."""
    spec, enemies = balance.merge, balance.enemies
    for field, name in (("enemy", spec.enemy), ("into", spec.into)):
        if name not in enemies:
            raise ValueError(f"merge.{field}: no existe el enemigo {name}")
    into = enemies[spec.into]
    shape = into.shape
    nearest = into.radius * math.cos(math.pi * max(shape.steps) / shape.vertices)
    if nearest <= balance.player.radius:
        raise ValueError(
            f"merge.into: su línea más cercana al centro queda a {nearest:.1f}, y"
            f" tocaría al jugador de radio {balance.player.radius}"
        )
