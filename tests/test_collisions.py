"""Tests de las colisiones: cada cuerpo es un círculo (ADR 0006)."""

from pygame.math import Vector2

from circlebh.world.collisions import circles_touch


def test_circulos_que_se_tocan() -> None:
    # Los centros a 20 y los radios suman 30: se superponen.
    assert circles_touch(Vector2(0, 0), 12.0, Vector2(20, 0), 18.0)


def test_circulos_tangentes_chocan() -> None:
    # La distancia es exactamente la suma de los radios: 3-4-5, 2 + 3 = 5.
    assert circles_touch(Vector2(1, 1), 2.0, Vector2(4, 5), 3.0)


def test_circulos_separados_no_chocan() -> None:
    # Separados por una unidad: distancia 6, radios que suman 5.
    assert not circles_touch(Vector2(0, 0), 2.0, Vector2(0, -6), 3.0)


def test_un_circulo_dentro_de_otro_choca() -> None:
    # Mismo centro: la distancia 0 no es un caso especial.
    assert circles_touch(Vector2(5, 5), 1.0, Vector2(5, 5), 10.0)
