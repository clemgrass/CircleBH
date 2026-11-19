"""Carga validada de dataclasses desde JSON, y la inversa.

La usan el balance (ADR 0004) y la configuración del juego (ADR 0018). Los tipos de campo
que entiende son `float`, `int`, `bool`, `str`, `tuple[...]` de largo fijo, otras
dataclasses y `dict[str, Dataclass]`. Un error nombra la ruta del campo: `player.speed`.
"""

import dataclasses
import json
import typing

type Json = dict[str, Json] | list[Json] | str | int | float | bool
"""Lo que `json` lee y escribe, sin `null`: ningún campo es opcional."""


class DataFileError(ValueError):
    """Un dato del archivo no calza con la dataclass. `field` es la ruta: `player.speed`."""

    def __init__(self, field: str, reason: str) -> None:
        super().__init__(f"{field}: {reason}" if field else reason)
        self.field = field
        self.reason = reason


def load[T](cls: type[T], data: object, field: str = "") -> T:
    """Convierte `data`, leído de un JSON, en una instancia de la dataclass `cls`.

    Un entero vale como `float`, pero un `bool` no vale como número: en Python,
    `True` es un `int`. Si falta un campo, sobra uno o un tipo no calza, lanza
    `DataFileError` con la ruta del campo, a partir de `field`.
    """
    return typing.cast(T, _load_value(cls, data, field))


def dump(obj: object) -> Json:
    """La inversa de `load`: una dataclass a dicts, listas y valores de JSON.

    Lanza `TypeError` con cualquier cosa que no sea un dato (una función, una `lambda`).
    """
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return {f.name: dump(getattr(obj, f.name)) for f in dataclasses.fields(obj)}
    if isinstance(obj, tuple):
        return [dump(item) for item in obj]
    if isinstance(obj, dict):
        return {str(key): dump(value) for key, value in obj.items()}
    if isinstance(obj, bool | int | float | str):
        return obj
    raise TypeError(f"no es un dato que se pueda guardar en JSON: {obj!r}")


def _load_value(kind: object, data: object, field: str) -> object:
    if isinstance(kind, type) and dataclasses.is_dataclass(kind):
        return _load_dataclass(kind, data, field)
    origin = typing.get_origin(kind)
    if origin is tuple:
        return _load_tuple(typing.get_args(kind), data, field)
    if origin is dict:
        _, value_kind = typing.get_args(kind)
        mapping = _expect_object(data, field)
        return {
            key: _load_value(value_kind, value, _join(field, key))
            for key, value in mapping.items()
        }
    if kind is float:
        # bool va antes: `isinstance(True, int)` es verdadero.
        if isinstance(data, bool) or not isinstance(data, int | float):
            raise _mismatch(field, "un número", data)
        return float(data)
    if kind in _SCALARS:
        # `type(...) is` y no `isinstance`, para que `true` no pase como entero.
        if type(data) is not kind:
            raise _mismatch(field, _SCALARS[kind], data)
        return data
    raise TypeError(f"{field}: tipo de campo no soportado: {kind!r}")


_SCALARS: dict[object, str] = {int: "un entero", bool: "true o false", str: "un texto"}


def _load_dataclass(cls: type, data: object, field: str) -> object:
    mapping = _expect_object(data, field)
    hints = typing.get_type_hints(cls)
    names = [f.name for f in dataclasses.fields(cls)]
    for name in names:
        if name not in mapping:
            raise DataFileError(_join(field, name), "falta el campo")
    for name in mapping:
        if name not in names:
            raise DataFileError(_join(field, name), "sobra el campo")
    values = {
        name: _load_value(hints[name], mapping[name], _join(field, name))
        for name in names
    }
    return cls(**values)


def _load_tuple(kinds: tuple[object, ...], data: object, field: str) -> object:
    if not isinstance(data, list) or len(data) != len(kinds):
        raise _mismatch(field, f"una lista de {len(kinds)} elementos", data)
    return tuple(
        _load_value(kind, item, f"{field}[{i}]")
        for i, (kind, item) in enumerate(zip(kinds, data, strict=True))
    )


def _expect_object(data: object, field: str) -> dict[str, object]:
    if not isinstance(data, dict):
        raise _mismatch(field, "un objeto", data)
    return data


def _mismatch(field: str, expected: str, data: object) -> DataFileError:
    shown = json.dumps(data, ensure_ascii=False)
    return DataFileError(field, f"se esperaba {expected}, llegó {shown}")


def _join(field: str, name: str) -> str:
    return f"{field}.{name}" if field else name
