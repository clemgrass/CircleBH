"""La semilla de cada partida. Se elige fuera del juego; dentro, el azar sale solo de
`Random(seed)` (ADR 0005)."""

import secrets


def random_seed() -> int:
    """Una semilla al azar, de 0 a 2³² − 1."""
    return secrets.randbelow(2**32)


def next_seed(first: int, game: int, *, demo: bool, fixed: bool) -> int:
    """La semilla de la partida número `game`. La primera es la 0, con `first`.

    - En la demo y las capturas, `first + game`: solo depende de la semilla inicial, así
      que repetir con la semilla impresa da lo mismo, también después de morir.
    - Jugando, `first` otra vez si se fijó con `--seed` (`fixed`); si no, una nueva.
    """
    if demo:
        return first + game
    return first if fixed else random_seed()
