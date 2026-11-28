"""La mano: las tarjetas que se ofrecen al subir de nivel (spec de la 0.3.0, "La mano",
y ADR 0029).

Todo aquí es puro: recibe lo que tiene el jugador (`Loadout`) y devuelve lo que
tendría. Así el mundo, la vista previa de la tarjeta y los tests usan lo mismo.
"""

import dataclasses
import random
import typing
from collections.abc import Mapping
from dataclasses import dataclass, replace

from circlebh.balance import (
    Balance,
    CardSpec,
    KnobChange,
    LevelUpSpec,
    NewWeaponChange,
    PlayerChange,
    PlayerSpec,
    WeaponSpec,
)


@dataclass(frozen=True)
class Offer:
    """Una tarjeta de la mano: cuál, para qué arma y con qué valor."""

    card: str
    """La clave de la tarjeta en `Balance.cards`."""

    weapon: str
    """El arma que cambia, como `"f2"`, o la que suma una tarjeta de arma nueva. `""` en
    las tarjetas del jugador."""

    value: float
    """El valor sorteado de la lista de la tarjeta. 0 en una de arma nueva."""


@dataclass(frozen=True)
class Loadout:
    """Lo que tiene el jugador, sin el mundo: lo que una tarjeta puede cambiar."""

    weapons: dict[str, WeaponSpec]
    """Sus armas, de `"f1"` en adelante, en el orden en que llegaron (`weapon_name`)."""

    player: PlayerSpec
    """Cómo es el jugador ahora."""

    rerolls: int
    """Cuántas veces puede cambiar la mano entera."""

    banishes: int
    """Cuántas tarjetas puede sacar todavía."""


def weapon_name(rank: int) -> str:
    """El nombre del arma de rango `rank`: `"f1"` para el 0, `"f2"` para el 1."""
    return f"f{rank + 1}"


def available(
    state: Loadout,
    cards: Mapping[str, CardSpec],
    spec: LevelUpSpec,
    banished: set[str],
) -> list[tuple[str, str]]:
    """Los pares (tarjeta, arma) que tienen efecto sobre `state`, en el orden de `cards`
    y de las armas. Una tarjeta del jugador va con el arma `""`, y una de arma nueva,
    con la `fₖ` que suma. No entran las sacadas con banish."""
    pairs: list[tuple[str, str]] = []
    for name, card in cards.items():
        if name in banished:
            continue
        for target in _targets(card, state, spec):
            if _values_with_effect(name, target, state, cards):
                pairs.append((name, target))
    return pairs


def deal(
    state: Loadout,
    cards: Mapping[str, CardSpec],
    spec: LevelUpSpec,
    banished: set[str],
    rng: random.Random,
) -> tuple[Offer, ...]:
    """Reparte una mano de `spec.hand_size` pares distintos con efecto, con `rng`.

    Si alguno cambia la clase de forma, al menos uno de la mano también: ese se sortea
    primero, entre los de forma. Con menos pares que `hand_size`, trae los que haya, y
    sin ninguno, la mano queda vacía. El valor de cada tarjeta se sortea entre los de su
    lista que tienen efecto.
    """
    pairs = available(state, cards, spec, banished)
    shaped = [pair for pair in pairs if cards[pair[0]].shape]
    hand: list[tuple[str, str]] = []
    if shaped:
        hand.append(rng.choice(shaped))
    rest = [pair for pair in pairs if pair not in hand]
    hand += rng.sample(rest, min(spec.hand_size - len(hand), len(rest)))
    rng.shuffle(hand)
    return tuple(
        Offer(name, target, rng.choice(_values_with_effect(name, target, state, cards)))
        for name, target in hand
    )


def apply(
    offer: Offer, state: Loadout, cards: Mapping[str, CardSpec], base: WeaponSpec
) -> Loadout:
    """Lo que tendría el jugador después de elegir `offer`. Un arma nueva parte igual a
    `base`, la función base del balance, aunque `f₁` ya esté mejorada (ADR 0033)."""
    change = cards[offer.card].change
    if isinstance(change, NewWeaponChange):
        return replace(state, weapons=state.weapons | {offer.weapon: base})
    return _improve(offer, state, change)


def _improve(
    offer: Offer, state: Loadout, change: KnobChange | PlayerChange
) -> Loadout:
    """Lo que tendría el jugador después de un cambio a algo que ya tiene: una perilla
    de un arma o el jugador."""
    match change:
        case KnobChange(field=field, op=op):
            spec = state.weapons[offer.weapon]
            changed = _change_path(spec, field.split("."), op, offer.value)
            return replace(state, weapons=state.weapons | {offer.weapon: changed})
        case PlayerChange(field="rerolls", op=op):
            uses = _operate(state.rerolls, op, offer.value)
            return replace(state, rerolls=round(uses))
        case PlayerChange(field="banishes", op=op):
            uses = _operate(state.banishes, op, offer.value)
            return replace(state, banishes=round(uses))
        case PlayerChange(field=field, op=op):
            player = _change_path(state.player, [field], op, offer.value)
            return replace(state, player=player)


def check_cards(balance: Balance) -> None:
    """Rechaza al crear el mundo una tarjeta que no se puede aplicar, nombrando el
    campo: una perilla de un campo que no es un número del arma, un arma que no puede
    haber (de `"f1"` a la de `level_up.max_weapons`) o una tarjeta sin valores."""
    names = {weapon_name(rank) for rank in range(balance.level_up.max_weapons)}
    for name, card in balance.cards.items():
        where = f"cards.{name}"
        for weapon in card.weapons:
            if weapon not in names:
                raise ValueError(f"{where}.weapons: no puede haber un arma {weapon}")
        change = card.change
        if isinstance(change, NewWeaponChange):
            continue
        if isinstance(change, KnobChange) and not _is_number_path(
            WeaponSpec, change.field.split(".")
        ):
            raise ValueError(
                f"{where}.change.field: {change.field} no es un número del arma"
            )
        if not change.values:
            raise ValueError(f"{where}.change.values: tiene que traer al menos uno")


def _targets(card: CardSpec, state: Loadout, spec: LevelUpSpec) -> list[str]:
    """A qué puede ir `card`: las armas que tienes y le sirven, el jugador (`""`) o la
    `fₖ` que sigue, si te cabe."""
    match card.change:
        case KnobChange():
            return [w for w in state.weapons if not card.weapons or w in card.weapons]
        case PlayerChange():
            return [""]
        case NewWeaponChange():
            count = len(state.weapons)
            return [weapon_name(count)] if count < spec.max_weapons else []


def _values_with_effect(
    name: str, target: str, state: Loadout, cards: Mapping[str, CardSpec]
) -> list[float]:
    """Los valores de la tarjeta que cambian algo en `state`. Una de arma nueva siempre
    tiene efecto, con el valor 0: llega aquí solo si el arma cabe."""
    change = cards[name].change
    if isinstance(change, NewWeaponChange):
        return [0.0]
    return [
        value
        for value in change.values
        if _improve(Offer(name, target, value), state, change) != state
    ]


def _operate(current: float, op: str, value: float) -> float:
    """`current + value` o `current · value`. Un entero queda entero, redondeado."""
    result = current + value if op == "add" else current * value
    return round(result) if isinstance(current, int) else result


def _change_path[T](obj: T, path: list[str], op: str, value: float) -> T:
    """Una copia de la dataclass `obj` con el número de la ruta `path` cambiado."""
    name, *rest = path
    current = getattr(obj, name)
    new = (
        _change_path(current, rest, op, value) if rest else _operate(current, op, value)
    )
    return replace(obj, **{name: new})  # type: ignore[type-var]


def _is_number_path(cls: type, path: list[str]) -> bool:
    """Si `path` lleva, dentro de la dataclass `cls`, a un campo `float` o `int`."""
    name, *rest = path
    hints = typing.get_type_hints(cls)
    if name not in {f.name for f in dataclasses.fields(cls)}:
        return False
    kind = hints[name]
    if rest:
        is_spec = isinstance(kind, type) and dataclasses.is_dataclass(kind)
        return is_spec and _is_number_path(kind, rest)
    return kind in (float, int)
