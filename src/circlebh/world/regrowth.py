"""La absorción: un herido que toca una línea suelta la recupera (decisión 68 de la spec
de la 0.2.0).

Es la misma regla para el paciente al que la donó el médico y para cualquier herido que
se cruce con ella. Se tocan por sus círculos envolventes: la red de seguridad no deja
que se monten, así que el contacto más cercano posible es tangente, y las líneas de uno
nunca alcanzarían a cruzar las del otro.
"""

from collections.abc import Sequence

from circlebh.world.actions import Deliver
from circlebh.world.collisions import circles_touch
from circlebh.world.enemy import Enemy
from circlebh.world.events import Event, Regrow

CONTACT_SLACK = 1e-6
"""Margen del contacto, en unidades del plano. La red de seguridad deja a un par justo
tangente, y por redondeo puede quedar a `1e-12` de tocarse."""


def absorb(enemies: Sequence[Enemy], step: int) -> tuple[list[Event], list[Enemy]]:
    """Cada línea suelta viva, en orden de aparición, la absorbe el primer herido de la
    lista que la toca: recupera su línea de índice menor que falta, en el paso `step`.

    Una línea en camino a su paciente no la absorbe quien la donó, que queda herido y en
    contacto con ella justo al soltarla. Devuelve los `Regrow` y las líneas absorbidas.
    """
    events: list[Event] = []
    absorbed: list[Enemy] = []
    for stray in (e for e in enemies if e.stray and e.alive):
        donor = _donor(stray)
        for patient in enemies:
            if (
                patient.wounded
                and not patient.stray
                and not patient.spec.phantom
                and patient is not donor
                and circles_touch(
                    stray.position,
                    stray.radius + CONTACT_SLACK,
                    patient.position,
                    patient.radius,
                )
            ):
                missing = set(range(patient.spec.shape.line_count)) - set(patient.edges)
                k = min(missing)
                patient.restore_edge(k, step)
                events.append(Regrow(patient, k))
                absorbed.append(stray)
                break
    return events, absorbed


def _donor(stray: Enemy) -> Enemy | None:
    """Quien la donó, mientras va a su paciente. Flotando, ya no tiene."""
    for action in stray.actions:
        if isinstance(action, Deliver) and action.patient is not None:
            return action.donor
    return None
