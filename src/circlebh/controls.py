"""La intención de movimiento: teclas y ejes del control convertidos en un `Vector2`.

La intención mide de 0 a 1 y usa las coordenadas de `world`, con Y hacia arriba.
`world` no sabe de dónde viene: aquí se juntan el teclado, el stick y la cruceta.
Leer los dispositivos es trabajo de `scenes/`; este módulo solo hace las cuentas.
"""

from pygame.math import Vector2

AXIS_MAX = 32767
"""El valor máximo de un eje del control en SDL. El mínimo es −32768."""


def keyboard_intent(*, left: bool, right: bool, up: bool, down: bool) -> Vector2:
    """Cuatro direcciones apretadas o no, en una intención de largo 0 o 1.

    La diagonal se normaliza: si no, avanzaría √2 veces más rápido.
    Sirve igual para la cruceta del control.
    """
    intent = Vector2(int(right) - int(left), int(up) - int(down))
    if intent.length_squared() > 0:
        intent.normalize_ip()
    return intent


def axis_to_unit(raw: int) -> float:
    """Un eje del control, de −32768 a 32767, en −1..1."""
    return max(raw / AXIS_MAX, -1.0)


def stick_intent(x: float, y: float, deadzone: float) -> Vector2:
    """La posición del stick, con cada eje en −1..1, en una intención de largo 0 a 1.

    - La Y se invierte: el stick da Y positiva hacia abajo, y `world` la usa hacia arriba.
    - Dentro de la zona muerta (un círculo de radio `deadzone`), da cero.
    - Fuera, reescala el largo para que el borde de la zona muerta valga 0 y el tope, 1.
    - La dirección no cambia.
    """
    intent = Vector2(x, -y)
    length = intent.length()
    if length <= deadzone:
        return Vector2()
    scaled = min((length - deadzone) / (1 - deadzone), 1.0)
    return intent * (scaled / length)


def combine(*intents: Vector2) -> Vector2:
    """Suma las intenciones de todas las fuentes y recorta el resultado a largo 1."""
    total = sum(intents, Vector2())
    return total.clamp_magnitude(1)
