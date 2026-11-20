"""La simulación sin ventana: el piloto juega 60 s, con reinicios (ADR 0007).

Corre en `poe check` y en la CI, no en `poe fast`.
"""

import pytest

from circlebh.balance import BALANCE
from circlebh.pilot import simulate


@pytest.mark.simulacion
def test_simulacion_de_60_s_sin_errores() -> None:
    assert simulate(BALANCE, seconds=60.0, seed=1) >= 1
