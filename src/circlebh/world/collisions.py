"""Colisiones: círculos (ADR 0006) y segmentos (ADR 0020)."""

import math

from pygame.math import Vector2


def circles_touch(a: Vector2, ra: float, b: Vector2, rb: float) -> bool:
    """Si el círculo de centro `a` y radio `ra` toca al de centro `b` y radio `rb`.

    Se tocan cuando la distancia entre los centros no pasa la suma de los radios.
    Tangentes cuenta como tocarse.
    """
    return a.distance_to(b) <= ra + rb


def crossing(p: Vector2, q: Vector2, a: Vector2, b: Vector2) -> float | None:
    """Dónde cruza el tramo `p→q` al segmento `ab`, como fracción `t ∈ [0, 1]` del tramo.

    Los puntos del tramo son `p + t·r` y los del segmento `a + u·s`, con `r = q − p` y
    `s = b − a`. Igualarlos y tomar el producto cruz 2D con `s` y con `r` despeja
    `t = (a − p) × s / (r × s)` y `u = (a − p) × r / (r × s)`. Hay cruce si los dos
    caen en `[0, 1]`. Si `r × s = 0`, son paralelos o colineales, y da `None`: un punto
    que avanza por la misma recta del segmento no lo cruza.
    """
    r = q - p
    s = b - a
    denominator = r.cross(s)
    if denominator == 0:
        return None
    ap = a - p
    t = ap.cross(s) / denominator
    u = ap.cross(r) / denominator
    if 0 <= t <= 1 and 0 <= u <= 1:
        return t
    return None


def closest_point_on_segment(p: Vector2, a: Vector2, b: Vector2) -> Vector2:
    """El punto del segmento `ab` más cercano a `p`.

    Es la proyección de `p` sobre la recta, `a + u·(b − a)` con
    `u = (p − a)·(b − a) / |b − a|²`, acotando `u` a `[0, 1]` para no salir del
    segmento. Si `a == b`, el segmento es un punto y devuelve `a`.
    """
    ab = b - a
    length_squared = ab.length_squared()
    if length_squared == 0:
        return Vector2(a)
    u = (p - a).dot(ab) / length_squared
    return a + ab * min(1.0, max(0.0, u))


def segment_touches_circle(
    a: Vector2, b: Vector2, center: Vector2, radius: float
) -> bool:
    """Si el segmento `ab` toca al círculo. Tangente cuenta como tocarlo."""
    return center.distance_to(closest_point_on_segment(center, a, b)) <= radius


def segment_circle_entry(
    start: Vector2, end: Vector2, center: Vector2, radius: float
) -> float | None:
    """Dónde entra el tramo `start→end` al círculo, como fracción `t ∈ [0, 1]` del tramo.

    Con `d = end − start` y `f = start − center`, el punto `start + t·d` está en el
    borde cuando `|f + t·d|² = radius²`, o sea `(d·d)·t² + 2(f·d)·t + (f·f − radius²) = 0`.
    La entrada es la raíz menor. Si `start` ya está adentro, da 0, y si el tramo no
    toca el círculo, `None`. Tangente cuenta como tocarlo.
    """
    f = start - center
    c = f.length_squared() - radius * radius
    if c <= 0:
        return 0.0
    a = end.distance_squared_to(start)
    b = f.dot(end - start)
    discriminant = b * b - a * c
    if a == 0 or discriminant < 0:
        return None
    t = (-b - math.sqrt(discriminant)) / a
    return t if 0 <= t <= 1 else None
