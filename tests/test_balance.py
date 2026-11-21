"""Tests de la coordinación entre `balance.py` y `balance.json` (ADR 0004)."""

import importlib.util
import json
import shutil
from dataclasses import dataclass, replace
from pathlib import Path
from types import ModuleType

import pytest

import circlebh.balance
from circlebh.balance import BALANCE, Balance, CoulombSpec, PlayerSpec, SeekSpec
from circlebh.balance_tools import (
    check,
    differences,
    export_json,
    import_json,
    load_json,
)
from circlebh.datafile import DataFileError, dump
from circlebh.world.clock import STEP

BALANCE_PY = Path(circlebh.balance.__file__)


def copia_de_balance_py(tmp_path: Path) -> Path:
    copia = tmp_path / "balance.py"
    shutil.copy(BALANCE_PY, copia)
    return copia


def con_jugador(speed: float, radius: float) -> Balance:
    """El balance real, con otro jugador: el resto no cambia entre los dos lados."""
    return replace(BALANCE, player=replace(BALANCE.player, speed=speed, radius=radius))


def json_con_jugador(player: dict[str, object]) -> str:
    """El JSON del balance real, con otro objeto `player`."""
    data = dump(BALANCE)
    assert isinstance(data, dict)
    return json.dumps(data | {"player": player})


def cargar_modulo(path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location("balance_copia", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# --- El chequeo ---


def test_balance_real_calza() -> None:
    assert differences(BALANCE, load_json()) == []


def test_chequeo_real_sin_errores() -> None:
    assert check() == []


def test_diferencia_nombra_el_campo() -> None:
    en_python = con_jugador(speed=3.0, radius=12.0)
    en_json = con_jugador(speed=2.5, radius=12.0)
    assert differences(en_python, en_json) == [
        "player.speed: balance.py=3.0, balance.json=2.5"
    ]


def test_todas_las_diferencias_se_reportan() -> None:
    en_python = con_jugador(speed=3.0, radius=12.0)
    en_json = con_jugador(speed=2.5, radius=10.0)
    assert differences(en_python, en_json) == [
        "player.speed: balance.py=3.0, balance.json=2.5",
        "player.radius: balance.py=12.0, balance.json=10.0",
    ]


@dataclass(frozen=True)
class Roster:
    enemies: dict[str, PlayerSpec]


def test_una_entrada_que_solo_esta_en_un_lado() -> None:
    hexagono = PlayerSpec(speed=60.0, radius=20.0, charge=0.0)
    pentagono = PlayerSpec(speed=80.0, radius=16.0, charge=0.0)
    en_python = Roster(enemies={"hexagon": hexagono})
    en_json = Roster(enemies={"hexagon": hexagono, "pentagon": pentagono})
    assert differences(en_python, en_json) == [
        'enemies.pentagon: balance.py=(no está), balance.json={"speed": 80.0, "radius": 16.0, "charge": 0.0}'
    ]


def test_chequeo_nombra_el_campo_de_un_json_invalido(tmp_path: Path) -> None:
    roto = tmp_path / "balance.json"
    roto.write_text(
        json_con_jugador({"speed": True, "radius": 12.0, "charge": -14.0}),
        encoding="utf-8",
    )
    assert check(roto) == [
        "balance.json: player.speed: se esperaba un número, llegó true"
    ]


def test_chequeo_con_un_json_que_no_es_json(tmp_path: Path) -> None:
    roto = tmp_path / "balance.json"
    roto.write_text('{"player": ', encoding="utf-8")
    [linea] = check(roto)
    assert linea.startswith("balance.json: no es JSON válido")


# --- Exportar e importar ---


def test_exportar_escribe_el_balance(tmp_path: Path) -> None:
    destino = tmp_path / "balance.json"
    export_json(destino)
    assert json.loads(destino.read_text(encoding="utf-8")) == {
        "player": {"speed": 240.0, "radius": 12.0, "charge": -14.0},
        "charges": {
            "k": 171000.0,
            "cutoff": 150.0,
            "softening": 1.0,
            "player_softening": 24.0,
            "core_strength": 30000.0,
            "core_reach": 1.2,
            "core_exponent": 4.0,
        },
        "enemies": {
            "hexagon": {
                "sides": 6,
                "radius": 24.0,
                "speed": 120.0,
                "friction": 2.0,
                "spin": 0.0,
                "charge_per_line": 1.0,
                "patterns": [{"kind": "seek", "strength": 240.0}, {"kind": "coulomb"}],
                "threat": 1.0,
                "actions": [],
            },
            "square": {
                "sides": 4,
                "radius": 20.0,
                "speed": 120.0,
                "friction": 2.0,
                "spin": 1.5,
                "charge_per_line": 1.0,
                "patterns": [{"kind": "seek", "strength": 240.0}, {"kind": "coulomb"}],
                "threat": 1.0,
                "actions": [],
            },
            "triangle": {
                "sides": 3,
                "radius": 14.0,
                "speed": 150.0,
                "friction": 3.0,
                "spin": 0.0,
                "charge_per_line": 1.0,
                "patterns": [
                    {
                        "kind": "orbit",
                        "radius": 280.0,
                        "stiffness": 4.0,
                        "tangential": 0.0,
                    },
                    {"kind": "coulomb"},
                ],
                "threat": 1.5,
                "actions": [
                    {
                        "kind": "charge",
                        "watch_distance": 320.0,
                        "telegraph": 0.5,
                        "speed": 720.0,
                        "duration": 0.8,
                        "cooldown": 2.0,
                    }
                ],
            },
        },
        "spawning": {
            "distance": 800.0,
            "max_per_step": 4,
            "formation_gap": 20.0,
            "formation_size": [3, 6],
        },
        # El tema es largo; basta con que salga entero y en su lugar.
        "director": dump(BALANCE.director),
        "point_weapon": {"cooldown": 0.6, "speed": 300.0, "range": 700.0},
    }


def test_exportar_e_importar_ida_y_vuelta(tmp_path: Path) -> None:
    json_path = tmp_path / "balance.json"
    py_path = copia_de_balance_py(tmp_path)
    export_json(json_path)
    import_json(json_path, py_path)
    assert py_path.read_text(encoding="utf-8") == BALANCE_PY.read_text(encoding="utf-8")


def test_importar_cambia_solo_el_bloque_de_datos(tmp_path: Path) -> None:
    json_path = tmp_path / "balance.json"
    json_path.write_text(
        json_con_jugador({"speed": 300, "radius": 12.0, "charge": -14.0}),
        encoding="utf-8",
    )
    py_path = copia_de_balance_py(tmp_path)
    import_json(json_path, py_path)

    assert dump(cargar_modulo(py_path).BALANCE) == dump(
        con_jugador(speed=300.0, radius=12.0)
    )
    original = BALANCE_PY.read_text(encoding="utf-8")
    nuevo = py_path.read_text(encoding="utf-8")
    assert original.replace("speed=240.0", "speed=300.0") == nuevo


def test_importar_rechaza_un_campo_desconocido(tmp_path: Path) -> None:
    json_path = tmp_path / "balance.json"
    json_path.write_text(
        json_con_jugador(
            {"speed": 240.0, "radius": 12.0, "charge": -14.0, "color": "rojo"}
        ),
        encoding="utf-8",
    )
    py_path = copia_de_balance_py(tmp_path)
    with pytest.raises(DataFileError) as error:
        import_json(json_path, py_path)
    assert error.value.field == "player.color"
    assert py_path.read_text(encoding="utf-8") == BALANCE_PY.read_text(encoding="utf-8")


def test_importar_exige_las_marcas_del_bloque(tmp_path: Path) -> None:
    json_path = tmp_path / "balance.json"
    export_json(json_path)
    py_path = tmp_path / "balance.py"
    py_path.write_text("BALANCE = None\n", encoding="utf-8")
    with pytest.raises(ValueError, match="marcas"):
        import_json(json_path, py_path)
    assert py_path.read_text(encoding="utf-8") == "BALANCE = None\n"


# --- Cargas y patrones (ADR 0021) ---


def test_hexagono_declara_seek_y_coulomb() -> None:
    patterns = BALANCE.enemies["hexagon"].patterns
    assert [type(p) for p in patterns] == [SeekSpec, CoulombSpec]


@pytest.mark.parametrize("nombre", sorted(BALANCE.enemies))
def test_rapidez_terminal_de_seek_no_pasa_speed(nombre: str) -> None:
    # Coherencia: con roce, la rapidez terminal de seek es strength / friction. Si pasa
    # `speed`, el tope sería lo único que lo frena.
    enemy = BALANCE.enemies[nombre]
    for pattern in enemy.patterns:
        if isinstance(pattern, SeekSpec):
            assert pattern.strength / enemy.friction <= enemy.speed


@pytest.mark.parametrize("nombre", sorted(BALANCE.enemies))
def test_el_giro_cabe_en_la_cota_del_golpe(nombre: str) -> None:
    # Coherencia (ADR 0027): `hit_by` coincide con los subpasos para `|ω·dt| ≤ 0,1`
    # (`test_rigid.py`). Un giro más rápido queda fuera de lo verificado.
    assert abs(BALANCE.enemies[nombre].spin * STEP) <= 0.1


@pytest.mark.parametrize("nombre", sorted(BALANCE.enemies))
def test_el_nucleo_alcanza_antes_del_corte(nombre: str) -> None:
    # La grilla busca vecinos hasta `cutoff`: si el núcleo alcanzara más lejos, no lo vería.
    radius = BALANCE.enemies[nombre].radius
    assert BALANCE.charges.core_reach * 2 * radius < BALANCE.charges.cutoff
