"""Escenarios de la demo: estados de partida con nombre, para capturas y pruebas (ADR 0013).

Cuando exista `world`, cada escenario va a armar su estado inicial.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Scenario:
    name: str
    description: str


SCENARIOS: dict[str, Scenario] = {
    scenario.name: scenario
    for scenario in [
        Scenario("plano-vacio", "El plano cartesiano, sin nada encima."),
    ]
}
