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


def test_captura_dos_tiempos_en_el_mismo_paso(
    capsys: pytest.CaptureFixture[str],
) -> None:
    # 0 y 0.001 caen en el paso 0: se captura ese paso una sola vez.
    main(["--demo", "--seed", "1", "--capture", "0,0.001"])

    assert capturas() == ["plano-vacio-seed1-t0.00.png"]
    assert capsys.readouterr().out.count("plano-vacio-seed1-t0.00.png") == 1


def test_tiempos_en_pasos_distintos_no_se_pisan() -> None:
    # 0.005 cae en el paso 0 y 0.009 en el paso 1 (1/60 = 0.0167 s).
    # El nombre lleva el tiempo del paso capturado, así que no se pisan.
    main(["--demo", "--seed", "1", "--capture", "0.005,0.009"])

    assert capturas() == ["plano-vacio-seed1-t0.00.png", "plano-vacio-seed1-t0.02.png"]


def test_captura_deja_pygame_cerrado() -> None:
    main(["--demo", "--seed", "1", "--capture", "0"])

    assert not pygame.get_init()
