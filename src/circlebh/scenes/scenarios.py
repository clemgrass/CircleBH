"""Escenarios de la demo: estados de partida con nombre, para capturas y pruebas (ADR 0013)."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Scenario:
    name: str
    description: str
    pilot: bool
    """Si el piloto mueve al jugador. Si no, el jugador se queda quieto."""


SCENARIOS: dict[str, Scenario] = {
    scenario.name: scenario
    for scenario in [
        Scenario(
            "jugador-moviendose",
            "El piloto da una vuelta completa cada 4 s.",
            pilot=True,
        ),
        Scenario(
            "enemigo-persigue",
            "El jugador quieto, y un hexágono que aparece fuera de la vista y lo alcanza.",
            pilot=False,
        ),
        Scenario(
            "anillo",
            "El piloto se mueve, y los anillos crecen donde nacieron, sin seguirlo.",
            pilot=True,
        ),
    ]
}
