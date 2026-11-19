"""Chequeo, exportación e importación del balance (ADR 0004).

`python -m circlebh.balance_tools chequear | exportar | importar`, o las tareas
`poe balance-*`. El juego corre `check()` al arrancar y no abre si hay diferencias.
"""

import argparse
import json
import subprocess
import sys
from collections.abc import Sequence
from importlib import resources
from pathlib import Path

from circlebh.balance import BALANCE, Balance
from circlebh.datafile import DataFileError, Json, dump, load

PACKAGE_DIR = Path(__file__).parent
"""Dónde viven `balance.py` y `balance.json` en el repo; exportar e importar escriben ahí."""

BLOCK_START = "# >>> datos (lo genera poe balance-importar)\n"
BLOCK_END = "# <<< datos\n"


def load_json(path: Path | None = None) -> Balance:
    """Lee y valida `balance.json`: por defecto, el del paquete, con `importlib.resources`."""
    if path is None:
        text = resources.files("circlebh").joinpath("balance.json").read_text("utf-8")
    else:
        text = path.read_text(encoding="utf-8")
    return load(Balance, json.loads(text))


def differences(in_python: object, in_json: object) -> list[str]:
    """Una línea por campo que difiere: `player.speed: balance.py=3.0, balance.json=2.5`."""
    lines: list[str] = []
    _compare(dump(in_python), dump(in_json), "", lines)
    return lines


def check(path: Path | None = None) -> list[str]:
    """Los errores del balance, listos para imprimir. Vacía si todo calza."""
    try:
        in_json = load_json(path)
    except json.JSONDecodeError as error:
        return [f"balance.json: no es JSON válido: {error}"]
    except DataFileError as error:
        return [f"balance.json: {error}"]
    return differences(BALANCE, in_json)


def export_json(path: Path) -> None:
    """Escribe `BALANCE` como JSON en `path` (Python → JSON)."""
    text = json.dumps(dump(BALANCE), indent=2, ensure_ascii=False)
    path.write_text(text + "\n", encoding="utf-8")


def import_json(json_path: Path, py_path: Path) -> None:
    """Reescribe el bloque de datos de `py_path` con lo que dice `json_path` (JSON → Python).

    El JSON se valida contra las clases de `balance.py` antes de tocar nada, y el
    resultado pasa por `ruff format`. Las clases y sus docstrings no cambian.
    """
    balance = load(Balance, json.loads(json_path.read_text(encoding="utf-8")))
    source = py_path.read_text(encoding="utf-8")
    # El repr de una dataclass ya es Python válido: `Balance(player=PlayerSpec(...))`.
    py_path.write_text(
        replace_data_block(source, f"BALANCE = {balance!r}\n"), encoding="utf-8"
    )
    subprocess.run(
        [sys.executable, "-m", "ruff", "format", "--quiet", str(py_path)], check=True
    )


def replace_data_block(source: str, code: str) -> str:
    """Cambia lo que hay entre `BLOCK_START` y `BLOCK_END` por `code`."""
    if source.count(BLOCK_START) != 1 or source.count(BLOCK_END) != 1:
        raise ValueError(
            "balance.py: las marcas del bloque de datos faltan o están repetidas"
        )
    head, rest = source.split(BLOCK_START)
    _, tail = rest.split(BLOCK_END)
    return f"{head}{BLOCK_START}{code}{BLOCK_END}{tail}"


def _compare(in_python: Json, in_json: Json, field: str, lines: list[str]) -> None:
    if isinstance(in_python, dict) and isinstance(in_json, dict):
        for key in in_python | in_json:
            path = f"{field}.{key}" if field else key
            if key not in in_json:
                lines.append(_line(path, _show(in_python[key]), "(no está)"))
            elif key not in in_python:
                lines.append(_line(path, "(no está)", _show(in_json[key])))
            else:
                _compare(in_python[key], in_json[key], path, lines)
    elif in_python != in_json:
        lines.append(_line(field, _show(in_python), _show(in_json)))


def _line(field: str, in_python: str, in_json: str) -> str:
    return f"{field}: balance.py={in_python}, balance.json={in_json}"


def _show(value: Json) -> str:
    return json.dumps(value, ensure_ascii=False)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="balance", description="Coordina balance.py y balance.json (ADR 0004)."
    )
    parser.add_argument(
        "command",
        choices=["chequear", "exportar", "importar"],
        help="chequear: compara; exportar: Python → JSON; importar: JSON → Python",
    )
    args = parser.parse_args(argv)
    json_path = PACKAGE_DIR / "balance.json"
    py_path = PACKAGE_DIR / "balance.py"

    if args.command == "exportar":
        export_json(json_path)
        print(f"escrito: {json_path}")
        return 0
    if args.command == "importar":
        try:
            import_json(json_path, py_path)
        except DataFileError as error:
            print(f"balance.json: {error}", file=sys.stderr)
            return 1
        except ValueError as error:
            # Incluye el JSON mal escrito (`JSONDecodeError`) y las marcas que faltan.
            print(error, file=sys.stderr)
            return 1
        print(f"escrito: {py_path}")
        return 0

    errors = check()
    for line in errors:
        print(line, file=sys.stderr)
    if errors:
        return 1
    print("balance.py y balance.json calzan")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
