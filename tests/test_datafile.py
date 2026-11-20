"""Tests de `datafile`: cargar un dict de JSON en dataclasses, y la inversa."""

from dataclasses import dataclass
from typing import Literal

import pytest
from hypothesis import given
from hypothesis import strategies as st

from circlebh.datafile import DataFileError, dump, load


@dataclass(frozen=True)
class Mover:
    speed: float
    sides: int


@dataclass(frozen=True)
class Camera:
    visible: bool
    name: str
    offset: tuple[float, float]


@dataclass(frozen=True)
class Game:
    player: Mover
    camera: Camera
    enemies: dict[str, Mover]


DATOS = {
    "player": {"speed": 240.0, "sides": 0},
    "camera": {"visible": True, "name": "principal", "offset": [0.0, 1.5]},
    "enemies": {"hexagon": {"speed": 60.0, "sides": 6}},
}


def falla_en(cls: type, data: object) -> DataFileError:
    with pytest.raises(DataFileError) as error:
        load(cls, data)
    return error.value


def test_carga_una_dataclass_anidada() -> None:
    assert load(Game, DATOS) == Game(
        player=Mover(speed=240.0, sides=0),
        camera=Camera(visible=True, name="principal", offset=(0.0, 1.5)),
        enemies={"hexagon": Mover(speed=60.0, sides=6)},
    )


def test_entero_vale_como_flotante() -> None:
    mover = load(Mover, {"speed": 3, "sides": 6})
    assert mover.speed == 3.0
    assert isinstance(mover.speed, float)


def test_bool_no_pasa_por_numero() -> None:
    assert falla_en(Mover, {"speed": True, "sides": 6}).field == "speed"


def test_bool_no_pasa_por_entero() -> None:
    assert falla_en(Mover, {"speed": 1.0, "sides": True}).field == "sides"


def test_flotante_no_vale_como_entero() -> None:
    assert falla_en(Mover, {"speed": 1.0, "sides": 6.5}).field == "sides"


def test_campo_que_falta() -> None:
    error = falla_en(Mover, {"speed": 1.0})
    assert error.field == "sides"
    assert "falta" in str(error)


def test_campo_que_sobra() -> None:
    error = falla_en(Mover, {"speed": 1.0, "sides": 6, "color": "rojo"})
    assert error.field == "color"
    assert "sobra" in str(error)


def test_tipo_equivocado_nombra_la_ruta() -> None:
    datos = {**DATOS, "player": {"speed": "x", "sides": 0}}
    error = falla_en(Game, datos)
    assert error.field == "player.speed"
    assert str(error).startswith("player.speed: ")


def test_ruta_dentro_de_un_diccionario() -> None:
    datos = {**DATOS, "enemies": {"hexagon": {"speed": 60.0, "sides": "seis"}}}
    assert falla_en(Game, datos).field == "enemies.hexagon.sides"


def test_tupla_de_largo_equivocado() -> None:
    camara = {"visible": True, "name": "principal", "offset": [0.0]}
    assert falla_en(Camera, camara).field == "offset"


def test_un_objeto_que_no_es_diccionario() -> None:
    assert falla_en(Game, {**DATOS, "player": [240.0, 0]}).field == "player"


def test_raiz_que_no_es_objeto_no_tiene_ruta() -> None:
    error = falla_en(Game, [1, 2])
    assert error.field == ""
    assert str(error) == "se esperaba un objeto, llegó [1, 2]"


def test_dump_da_json_plano() -> None:
    assert dump(load(Game, DATOS)) == DATOS


def test_dump_rechaza_lo_que_no_es_dato() -> None:
    @dataclass(frozen=True)
    class WithFunction:
        rule: object

    with pytest.raises(TypeError):
        dump(WithFunction(rule=lambda: 1))


numeros = st.floats(allow_nan=False, allow_infinity=False)


@given(
    speed=numeros,
    sides=st.integers(),
    offset=st.tuples(numeros, numeros),
    name=st.text(),
    enemies=st.dictionaries(st.text(), st.builds(Mover, numeros, st.integers())),
)
def test_dump_y_load_ida_y_vuelta(
    speed: float,
    sides: int,
    offset: tuple[float, float],
    name: str,
    enemies: dict[str, Mover],
) -> None:
    game = Game(
        player=Mover(speed=speed, sides=sides),
        camera=Camera(visible=False, name=name, offset=offset),
        enemies=enemies,
    )
    assert load(Game, dump(game)) == game


# --- Listas de patrones elegidos por `kind` (ADR 0021) ---


@dataclass(frozen=True, kw_only=True)
class _Seek:
    kind: Literal["seek"] = "seek"
    strength: float


@dataclass(frozen=True, kw_only=True)
class _Coulomb:
    kind: Literal["coulomb"] = "coulomb"


type _Pattern = _Seek | _Coulomb


@dataclass(frozen=True)
class _Holder:
    patterns: tuple[_Pattern, ...]


def test_lista_de_patrones_ida_y_vuelta() -> None:
    datos = {"patterns": [{"kind": "seek", "strength": 2}, {"kind": "coulomb"}]}
    holder = load(_Holder, datos)
    assert holder == _Holder((_Seek(strength=2.0), _Coulomb()))
    assert dump(holder) == {
        "patterns": [{"kind": "seek", "strength": 2.0}, {"kind": "coulomb"}]
    }


def test_lista_vacia_es_valida() -> None:
    assert load(_Holder, {"patterns": []}).patterns == ()


def test_kind_desconocido_nombra_la_ruta() -> None:
    datos = {"patterns": [{"kind": "seek", "strength": 1}, {"kind": "dash"}]}
    error = falla_en(_Holder, datos)
    assert error.field == "patterns[1].kind"
    assert "seek" in error.reason and "coulomb" in error.reason


def test_patron_sin_kind_nombra_la_ruta() -> None:
    error = falla_en(_Holder, {"patterns": [{"strength": 1}]})
    assert error.field == "patterns[0].kind"
    assert error.reason == "falta el campo"


def test_campo_que_sobra_en_un_patron() -> None:
    error = falla_en(_Holder, {"patterns": [{"kind": "coulomb", "k": 1}]})
    assert error.field == "patterns[0].k"


def test_lista_donde_va_objeto() -> None:
    error = falla_en(_Holder, {"patterns": {"kind": "seek"}})
    assert error.field == "patterns"


def test_literal_rechaza_otro_valor() -> None:
    # Directo contra un miembro de la unión: su `kind` es fijo.
    error = falla_en(_Seek, {"kind": "coulomb", "strength": 1})
    assert error.field == "kind"
