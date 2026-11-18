"""Tests del modo captura sin ventana (spec de capturas sin ventana).

Abren pygame con el driver `dummy` de SDL, así que corren sin pantalla, también en la CI.
"""

from pathlib import Path

import pygame
import pytest

from circlebh.__main__ import capture_path, main


@pytest.fixture(autouse=True)
def carpeta_temporal(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Cada test corre en una carpeta vacía, sin `.capturas/`."""
    monkeypatch.chdir(tmp_path)


def capturas() -> list[str]:
    return sorted(path.name for path in Path(".capturas").glob("*.png"))


def test_capture_path() -> None:
    assert capture_path("plano-vacio", 1, 1.0) == Path(
        ".capturas/plano-vacio-seed1-t1.00.png"
    )


def test_captura_de_punta_a_punta() -> None:
    main(["--demo", "--seed", "1", "--capture", "0,1"])

    assert capturas() == ["plano-vacio-seed1-t0.00.png", "plano-vacio-seed1-t1.00.png"]
    for name in capturas():
        assert pygame.image.load(Path(".capturas") / name).get_size() == (1280, 720)


def test_captura_dos_tiempos_en_el_mismo_paso() -> None:
    # 0 y 0.001 caen en el paso 0 y comparten nombre (t0.00): queda un archivo, sin error.
    main(["--demo", "--seed", "1", "--capture", "0,0.001"])

    assert capturas() == ["plano-vacio-seed1-t0.00.png"]


def test_captura_deja_pygame_cerrado() -> None:
    main(["--demo", "--seed", "1", "--capture", "0"])

    assert not pygame.get_init()
