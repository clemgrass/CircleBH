"""Tests de la línea de comandos (spec de capturas sin ventana)."""

import pytest

from circlebh.cli import RunOptions, parse_args


def falla_con_codigo_2(argv: list[str]) -> None:
    with pytest.raises(SystemExit) as salida:
        parse_args(argv)
    assert salida.value.code == 2


def test_opciones_completas() -> None:
    argv = ["--demo", "--scenario", "enemigo-persigue", "--seed", "7", "--speed", "2"]
    extra = ["--capture", "0,1,2", "--window", "1600x900"]
    assert parse_args([*argv, *extra]) == RunOptions(
        demo=True,
        scenario="enemigo-persigue",
        seed=7,
        seed_fixed=True,
        speed=2.0,
        capture=(0.0, 1.0, 2.0),
        window=(1600, 900),
    )


def test_valores_por_defecto() -> None:
    options = parse_args([])
    assert options.demo is False
    assert options.scenario == "enemigo-persigue"
    assert options.speed == 1.0
    assert options.capture == ()
    assert options.window == (1280, 720)
    assert isinstance(options.seed, int)
    assert options.seed >= 0


def test_capture_ordena_y_quita_repetidos() -> None:
    assert parse_args(["--demo", "--capture", "2,0,2"]).capture == (0.0, 2.0)


def test_capture_acepta_espacios() -> None:
    assert parse_args(["--demo", "--capture", "0, 1"]).capture == (0.0, 1.0)


def test_capture_exige_demo() -> None:
    falla_con_codigo_2(["--capture", "0"])


def test_escenario_desconocido() -> None:
    falla_con_codigo_2(["--scenario", "nada"])


@pytest.mark.parametrize("speed", ["0", "-1"])
def test_speed_debe_ser_positiva(speed: str) -> None:
    falla_con_codigo_2(["--speed", speed])


def test_capture_rechaza_negativos() -> None:
    falla_con_codigo_2(["--demo", "--capture", "-1"])


def test_capture_rechaza_texto() -> None:
    falla_con_codigo_2(["--demo", "--capture", "a,b"])


@pytest.mark.parametrize("tiempo", ["inf", "nan"])
def test_capture_rechaza_tiempos_no_finitos(tiempo: str) -> None:
    # Con inf, el modo captura no terminaría nunca.
    falla_con_codigo_2(["--demo", "--capture", tiempo])


def test_seed_negativa() -> None:
    falla_con_codigo_2(["--seed", "-1"])


def test_seed_fijada() -> None:
    options = parse_args(["--seed", "7"])
    assert options.seed == 7
    assert options.seed_fixed is True


def test_seed_cero_tambien_esta_fijada() -> None:
    # Borde: 0 es una semilla válida, no "sin semilla".
    assert parse_args(["--seed", "0"]).seed_fixed is True


def test_sin_seed_no_esta_fijada() -> None:
    assert parse_args([]).seed_fixed is False


def test_window_lee_ancho_por_alto() -> None:
    assert parse_args(["--window", "800x600"]).window == (800, 600)


def test_window_minima_vale() -> None:
    assert parse_args(["--window", "1x1"]).window == (1, 1)


@pytest.mark.parametrize(
    "window", ["0x720", "1280x0", "-1x720", "1280", "axb", "1280x720x3"]
)
def test_window_invalida(window: str) -> None:
    falla_con_codigo_2(["--window", window])
