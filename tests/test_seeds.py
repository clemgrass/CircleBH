"""Tests de la semilla de cada partida (spec, "Morir y reiniciar")."""

from circlebh.seeds import next_seed, random_seed


def test_jugando_con_seed_fijada_se_repite() -> None:
    assert next_seed(7, game=3, demo=False, fixed=True) == 7


def test_seed_cero_fijada_se_repite() -> None:
    # Borde: 0 es una semilla válida, no "sin semilla".
    assert next_seed(0, game=1, demo=False, fixed=True) == 0


def test_demo_usa_la_semilla_inicial_mas_n() -> None:
    # En la demo y las capturas, la partida n sale solo de la semilla inicial: así
    # repetir con la semilla impresa da los mismos PNG, también tras morir. Vale igual
    # si la semilla se fijó o se sorteó.
    for fixed in (True, False):
        partidas = [next_seed(7, game=n, demo=True, fixed=fixed) for n in (1, 2, 3)]
        assert partidas == [8, 9, 10]


def test_jugando_sin_seed_cada_reinicio_trae_una_nueva() -> None:
    semillas = {next_seed(7, game=1, demo=False, fixed=False) for _ in range(20)}
    # Propiedad, no valor: todas en rango, y no todas iguales. Que 20 sorteos en 2³²
    # salgan iguales tiene una probabilidad despreciable.
    assert all(0 <= semilla < 2**32 for semilla in semillas)
    assert len(semillas) > 1


def test_random_seed_en_rango() -> None:
    assert all(0 <= random_seed() < 2**32 for _ in range(20))
