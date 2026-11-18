"""Tests de la línea de comandos (spec de capturas sin ventana)."""

import pytest

from circlebh.cli import RunOptions, parse_args


def falla_con_codigo_2(argv: list[str]) -> None:
    with pytest.raises(SystemExit) as salida:
        parse_args(argv)
    assert salida.value.code == 2


def test_opciones_completas() -> None:
    argv = ["--demo", "--scenario", "plano-vacio", "--seed", "7", "--speed", "2"]
    assert parse_args([*argv, "--capture", "0,1,2"]) == RunOptions(
        demo=True,
        scenario="plano-vacio",
        seed=7,
        speed=2.0,
        capture=(0.0, 1.0, 2.0),
    )


def test_valores_por_defecto() -> None:
    options = parse_args([])
    assert options.demo is False
    assert options.scenario == "plano-vacio"
    assert options.speed == 1.0
    assert options.capture == ()
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
