"""Escenarios de la demo: estados de partida con nombre, para capturas y pruebas (ADR 0013)."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Scenario:
    name: str
    description: str
    pilot: bool
    """Si el piloto mueve al jugador. Si no, el jugador se queda quieto."""
    crowd: int = 0
    """Enemigos extra al empezar, en una red triangular alrededor del jugador."""
    crowd_enemy: str = "hexagon"
    """El tipo de esos enemigos, una clave de `enemies` en el balance."""
    lethal: bool = True
    """Si el contacto termina la partida."""
    armed: bool = True
    """Si el jugador tiene armas."""


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
            "punto-quita-lineas",
            "El piloto se mueve, y cada bala le quita al hexágono la línea que golpea"
            " hasta que desaparece.",
            pilot=True,
        ),
        Scenario(
            "oleadas",
            "El piloto se mueve, y los hexágonos llegan con la forma del tema"
            " (ADR 0025). La consola anota cada sección. Al morir, la partida se"
            " reinicia sola.",
            pilot=True,
        ),
        Scenario(
            "cuadrantes",
            "El piloto se mueve, armado y sin morir, por el tema entero. Lo comprado"
            " nace en el cuadrante más vacío, solo o en formación, y la ráfaga de un"
            " drop entra por los cuatro lados.",
            pilot=True,
            lethal=False,
        ),
        Scenario(
            "panal",
            "40 hexágonos alrededor del jugador quieto, sin contacto ni arma: se"
            " ordenan como imanes (ADR 0021).",
            pilot=False,
            crowd=40,
            lethal=False,
            armed=False,
        ),
        Scenario(
            "cuadrado-gira",
            "6 cuadrados que giran alrededor del jugador quieto, que no muere y les"
            " dispara: cada bala quita la línea que de verdad golpea (ADR 0027).",
            pilot=False,
            crowd=6,
            crowd_enemy="square",
            lethal=False,
        ),
        Scenario(
            "cuadrado-herido",
            "Un cuadrado que gira y llega al jugador quieto, que no muere y le dispara:"
            " con cada línea que pierde, gira en torno a su nuevo centro de masa"
            " (ADR 0027).",
            pilot=False,
            crowd=1,
            crowd_enemy="square",
            lethal=False,
        ),
        Scenario(
            "triangulo-embiste",
            "Un triángulo junto al piloto, que no muere ni dispara. El triángulo lo mira"
            " con una punta, avisa retrocediendo como un resorte, se suelta hacia donde"
            " está y el piloto lo esquiva al seguir su vuelta. Después se recupera,"
            " vuelve a su distancia y repite.",
            pilot=True,
            crowd=1,
            crowd_enemy="triangle",
            lethal=False,
            armed=False,
        ),
        Scenario(
            "pentagono-dispara",
            "3 pentágonos junto al piloto, que no muere ni dispara. Se alejan a su"
            " distancia, avisan dejando de girar y disparan una ráfaga: cada punta deja"
            " un brazo de espiral, con el color de acento.",
            pilot=True,
            crowd=3,
            crowd_enemy="pentagon",
            lethal=False,
            armed=False,
        ),
    ]
}
