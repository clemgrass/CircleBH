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
    crowd_center: tuple[float, float] = (0.0, 0.0)
    """El centro de esa red, relativo al jugador."""
    crowd_spacing: float = 90.0
    """La separación de esa red. 90 es más abierta que el equilibrio (≈ 55)."""
    guest: str | None = None
    """Un enemigo más al empezar, como el círculo que persigue al jugador."""
    guest_at: tuple[float, float] = (0.0, 0.0)
    """Dónde nace el invitado, relativo al jugador."""
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
        Scenario(
            "estrella",
            "Una estrella quieta junto al jugador quieto, que no muere y le dispara:"
            " cada bala le quita primero un lado, y después la diagonal que quedó"
            " expuesta.",
            pilot=False,
            crowd=1,
            crowd_enemy="star",
            lethal=False,
        ),
        Scenario(
            "estrella-rodeada",
            "Una estrella quieta junto al jugador quieto, que no muere ni dispara: los"
            " hexágonos y cuadrados que trae el tema la rodean sin encimarse, y no la"
            " mueven.",
            pilot=False,
            crowd=1,
            crowd_enemy="star",
            lethal=False,
            armed=False,
        ),
        Scenario(
            "gran-estrella",
            "5 estrellas alrededor del piloto, que no muere y dispara: se juntan, el aviso"
            " titila tres pulsos encima de él, y la gran estrella roja lo encierra"
            " mientras el enjambre la atraviesa. Al salir, se apaga.",
            pilot=True,
            crowd=5,
            crowd_enemy="star",
            lethal=False,
        ),
        Scenario(
            "circulo-dispersa",
            "7 hexágonos juntos a un lado del jugador quieto, que no muere ni dispara,"
            " y un círculo que nace bajo ellos: los atrae al cruzarlos, se los lleva en"
            " media vuelta alrededor del jugador, los suelta y sigue en espiral.",
            pilot=False,
            crowd=7,
            crowd_center=(250.0, 0.0),
            crowd_spacing=50.0,
            guest="circle",
            guest_at=(250.0, -160.0),
            lethal=False,
            armed=False,
        ),
        Scenario(
            "persecucion",
            "El piloto da vueltas, sin armas y sin morir, con un círculo que lo persigue"
            " en espiral: mira solo dónde está el piloto, no cómo se mueve, así que"
            " queda atrás cuando corre y se cierra cuando frena.",
            pilot=True,
            guest="circle",
            guest_at=(400.0, 0.0),
            lethal=False,
            armed=False,
        ),
        Scenario(
            "octagono-cerco",
            "10 octágonos alrededor del piloto, que no muere y dispara: se reparten por"
            " su anillo, giran antihorario y viajan con él sin tocarlo, porque su roce"
            " se mide desde el piloto. Las balas les van quitando líneas.",
            pilot=True,
            crowd=10,
            crowd_enemy="octagon",
            lethal=False,
        ),
        Scenario(
            "masa-critica",
            "30 hexágonos juntos a un lado del jugador quieto, que no muere ni dispara:"
            " la masa crítica trae un círculo, que nace fuera de la vista detrás del"
            " grupo, lo cruza, se lleva a parte al otro lado y los suelta.",
            pilot=False,
            crowd=30,
            crowd_center=(320.0, 0.0),
            crowd_spacing=55.0,
            lethal=False,
            armed=False,
        ),
    ]
}
