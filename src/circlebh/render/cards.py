"""La mano en pantalla: las tarjetas, con su frente y su reverso (spec de la 0.3.0,
decisiones 8, 9 y 11).

- **El frente** lleva el tipo, el símbolo grande, el verbo y el arma en movimiento, como
  quedaría con la tarjeta puesta. Sin precio ni texto explicativo.
- **El reverso** lleva la fórmula, lo viejo tachado y lo nuevo subrayado, y el precio.
- **La elegida** se marca con el color intermedio de la luz (ADR 0031).
- **El juego detrás** queda oscuro, con `dt = 0` en una esquina.

Las letras son de Tektur (OFL 1.1), que viaja completa dentro del paquete: trae `∫`, `n̂`
y los subíndices de las fórmulas. Los tamaños van en unidades del plano, así que
escalan con la cámara.
"""

import io
import math
from dataclasses import dataclass
from functools import cache, lru_cache
from importlib import resources

import pygame
from pygame.math import Vector2

from circlebh.balance import (
    CardSpec,
    KnobChange,
    NewWeaponChange,
    PlayerChange,
    PlayerSpec,
    WeaponSpec,
)
from circlebh.datafile import Json, dump
from circlebh.render.palette import Palette
from circlebh.viewport import Viewport
from circlebh.world.cards import Loadout, apply
from circlebh.world.game import World
from circlebh.world.terms import advance_at, projectile_offset

CARD_SIZE = (300.0, 420.0)
"""El ancho y el alto de una tarjeta, en unidades del plano."""
CARD_GAP = 40.0
"""El espacio entre dos tarjetas, en unidades del plano."""
CARD_LINE = 2.0
"""El grosor del borde de una tarjeta, en unidades del plano."""
SELECTED_LINE = 4.0
"""El grosor del borde de la tarjeta elegida, en unidades del plano."""
SHADE_ALPHA = 190
"""Cuánto se oscurece el juego detrás de la mano, de 0 a 255."""
LIFT = 0.15
"""Cuánto se corre la tarjeta hacia su lado al darse vuelta, como fracción de su alto:
así se ve si gira hacia arriba o hacia abajo."""
FONT_SIZES = 16
"""Cuántos tamaños de letra se guardan: la mano usa seis, y al cambiar el tamaño de la
ventana, los de antes se sueltan."""
TEXT_FIT = 0.86
"""Lo más ancho que puede ser un texto, como fracción del ancho de la tarjeta."""
PREVIEW_SECONDS = 8.0
"""Lo más que vive un proyectil en la vista previa: una mina quieta no se acumula."""

FAMILY_NAMES = {
    "knob": "PERILLA",
    "term": "SUMA",
    "operator": "OPERADOR",
    "weapon": "ARMA NUEVA",
    "player": "JUGADOR",
}
"""El tipo que muestra la tarjeta arriba, por su `family`."""

SYMBOLS = {
    "advance.coefficient": "v",
    "cooldown": "cooldown",
    "reach": "alcance",
    "spin": "Ω",
    "tau": "τ",
    "copies": "n",
    "speed": "speed",
    "radius": "r",
    "charge": "q",
    "rerolls": "rerolls",
    "banishes": "banishes",
}
"""Cómo se escribe cada campo en el reverso. Uno que no está aquí va con su ruta."""

UNITS = {"cooldown": " s", "tau": " s", "spin": " rad/s"}
"""Las unidades que se escriben después del valor."""

PLAYER_FORMULAS = {
    "speed": "|ṗ| ≤ speed",
    "radius": "choca a r del centro",
    "charge": "F = k·q·Q / d²",
    "rerolls": "cambiar la mano entera",
    "banishes": "sacar una tarjeta",
}
"""La fórmula del reverso de una tarjeta del jugador, por el campo que cambia."""


@dataclass(frozen=True)
class Change:
    """Un número que cambia la tarjeta: cómo se llama, cuánto vale y cuánto valdría."""

    name: str
    old: str
    new: str


@dataclass(frozen=True)
class CardView:
    """Lo que muestra una tarjeta de la mano."""

    spec: CardSpec
    weapon: WeaponSpec | None
    """El arma como quedaría con la tarjeta puesta, o `None` en las del jugador."""
    player: PlayerSpec
    """El jugador como quedaría."""
    changes: tuple[Change, ...]
    """Lo que cambia, para el reverso."""


@dataclass(frozen=True)
class CardPose:
    """Cómo está una tarjeta en este cuadro."""

    face: int
    """La cara a la que va o en la que está: 0 es el frente y 1, el reverso."""
    flip: float
    """Cuánto lleva del giro hacia `face`, de 0 a 1. Con 1, ya llegó."""
    direction: int
    """Hacia dónde gira: −1 hacia arriba y 1 hacia abajo."""


@dataclass(frozen=True)
class HandPose:
    """Cómo se ve la mano en este cuadro: lo que la escena decide y anima."""

    cards: tuple[CardPose, ...]
    selected: int
    rise: float
    """Cuánto subieron las tarjetas, de 0 (fuera de la pantalla) a 1 (en el medio)."""
    shade: float
    """Cuánto se oscurece el juego, de 0 a 1."""
    time: float
    """Los segundos de la vista previa del arma: corre aunque el mundo esté quieto."""
    hint: str
    """Las teclas, al pie. Vacío en la demo, que no lee la entrada."""


def card_views(world: World) -> list[CardView]:
    """Lo que muestra cada tarjeta de la mano de `world`, con la tarjeta puesta."""
    before = world.loadout
    views = []
    for offer in world.hand:
        spec = world.balance.cards[offer.card]
        after = apply(offer, before, world.balance.cards, world.balance.weapons)
        if isinstance(spec.change, PlayerChange):
            changes = _diff(_player_numbers(before), _player_numbers(after))
            views.append(CardView(spec, None, after.player, changes))
            continue
        weapon = after.weapons[offer.weapon]
        old = before.weapons.get(offer.weapon)
        changes = () if old is None else _diff(dump(old), dump(weapon))
        views.append(CardView(spec, weapon, after.player, changes))
    return views


def draw_hand(
    screen: pygame.Surface,
    viewport: Viewport,
    views: list[CardView],
    pose: HandPose,
    palette: Palette,
) -> None:
    """La sombra sobre el juego, `dt = 0`, las tarjetas y las teclas al pie."""
    left, top, width, height = viewport.rect
    shade = pygame.Surface((width, height), pygame.SRCALPHA)
    shade.fill((*palette.background.rgb, round(SHADE_ALPHA * pose.shade)))
    screen.blit(shade, (left, top))
    if pose.rise > 0:
        # Con las tarjetas: en el frenado, el juego todavía no está quieto.
        label = font(viewport.width(22)).render("dt = 0", True, palette.foreground)
        label.set_alpha(round(255 * pose.rise))
        margin = viewport.width(24)
        screen.blit(label, (left + margin, top + margin))

    card_w, card_h = (viewport.width(size) for size in CARD_SIZE)
    gap = viewport.width(CARD_GAP)
    row = len(views) * card_w + (len(views) - 1) * gap
    x = left + (width - row) / 2
    rest_y = top + (height - card_h) / 2
    # Sale desde abajo y frena al llegar: `1 − (1 − u)³`.
    eased = 1 - (1 - pose.rise) ** 3
    y = rest_y + (1 - eased) * (top + height - rest_y)
    for index, (view, card) in enumerate(zip(views, pose.cards, strict=True)):
        surface = _card_surface(
            view,
            card,
            index == pose.selected,
            (card_w, card_h),
            viewport,
            pose,
            palette,
        )
        squash = abs(math.cos(math.pi * card.flip))
        shown = pygame.transform.scale(
            surface, (card_w, max(1, round(card_h * squash)))
        )
        lift = card.direction * math.sin(math.pi * card.flip) * LIFT * card_h
        screen.blit(shown, (x, y + (card_h - shown.get_height()) / 2 + lift))
        x += card_w + gap

    if pose.hint:
        hint = font(viewport.width(18)).render(pose.hint, True, palette.foreground)
        hint.set_alpha(round(200 * eased))
        hint_y = y + card_h + viewport.width(28)
        screen.blit(hint, (left + (width - hint.get_width()) / 2, hint_y))


def _card_surface(
    view: CardView,
    card: CardPose,
    selected: bool,
    size: tuple[int, int],
    viewport: Viewport,
    pose: HandPose,
    palette: Palette,
) -> pygame.Surface:
    """La tarjeta entera, del tamaño final: la cara que se ve en este momento del giro,
    y el borde. En la primera mitad del giro todavía se ve la cara de antes."""
    surface = pygame.Surface(size, pygame.SRCALPHA)
    rect = surface.get_rect()
    pygame.draw.rect(surface, palette.background, rect)
    face = card.face if card.flip >= 0.5 else 1 - card.face
    if face == 0:
        _draw_front(surface, view, viewport, pose.time, palette)
    else:
        _draw_back(surface, view, viewport, palette)
    if selected:
        color, line = palette.light.selection, SELECTED_LINE
    else:
        color, line = palette.foreground, CARD_LINE
    pygame.draw.rect(surface, color, rect, viewport.width(line))
    return surface


def _draw_front(
    surface: pygame.Surface,
    view: CardView,
    viewport: Viewport,
    time: float,
    palette: Palette,
) -> None:
    """El tipo arriba, el símbolo grande, el verbo y, abajo, el arma en movimiento."""
    w, h = surface.get_size()
    fg = palette.foreground
    _centered(surface, FAMILY_NAMES[view.spec.family], 16, 0.08, viewport, fg)
    _centered(surface, view.spec.symbol, 40, 0.24, viewport, fg)
    _centered(surface, view.spec.title, 20, 0.39, viewport, fg)
    pad = viewport.width(20)
    box = pygame.Rect(pad, round(h * 0.5), w - 2 * pad, round(h * 0.44))
    if view.weapon is not None:
        _draw_weapon_preview(surface, box, view.weapon, viewport, time, palette)
    else:
        _draw_player_preview(surface, box, view.player, viewport, time, palette)


def _draw_back(
    surface: pygame.Surface, view: CardView, viewport: Viewport, palette: Palette
) -> None:
    """La fórmula, lo que cambia (lo viejo tachado y lo nuevo subrayado) y el precio."""
    fg = palette.foreground
    _centered(surface, FAMILY_NAMES[view.spec.family], 16, 0.08, viewport, fg)
    match view.spec.change:
        case PlayerChange(field=field):
            formula = PLAYER_FORMULAS[field]
        case KnobChange() | NewWeaponChange():
            assert view.weapon is not None
            formula = weapon_formula(view.weapon)
    _centered(surface, formula, 20, 0.24, viewport, fg)
    y = 0.42
    for change in view.changes:
        _draw_change(surface, change, y, viewport, palette)
        y += 0.11
    if isinstance(view.spec.change, NewWeaponChange):
        _centered(surface, "un arma más", 18, y, viewport, fg)
    _centered(surface, "precio: ninguno", 16, 0.88, viewport, fg)


def _draw_change(
    surface: pygame.Surface,
    change: Change,
    height: float,
    viewport: Viewport,
    palette: Palette,
) -> None:
    """`nombre = viejo nuevo`, con lo viejo tachado y lo nuevo subrayado."""
    letters = font(viewport.width(20))
    fg = palette.foreground
    parts = [
        letters.render(f"{change.name} = ", True, fg),
        letters.render(change.old, True, fg),
        letters.render("  ", True, fg),
        letters.render(change.new, True, fg),
    ]
    parts[1].set_alpha(150)
    total = sum(part.get_width() for part in parts)
    x = (surface.get_width() - total) / 2
    y = surface.get_height() * height - parts[0].get_height() / 2
    line = viewport.width(1.5)
    for index, part in enumerate(parts):
        surface.blit(part, (x, y))
        if index == 1:
            middle = y + part.get_height() * 0.55
            pygame.draw.line(
                surface, fg, (x, middle), (x + part.get_width(), middle), line
            )
        if index == 3:
            under = y + part.get_height() * 0.92
            pygame.draw.line(
                surface, fg, (x, under), (x + part.get_width(), under), line
            )
        x += part.get_width()


def _draw_weapon_preview(
    surface: pygame.Surface,
    box: pygame.Rect,
    spec: WeaponSpec,
    viewport: Viewport,
    time: float,
    palette: Palette,
) -> None:
    """El arma disparando sola hacia la derecha, sin enemigos, con los mismos términos
    que en el plano (`world/terms.py`). El alcance llena la caja."""
    origin = Vector2(box.left + viewport.width(8), box.centery)
    scale = (box.width - viewport.width(16)) / spec.reach
    dot = max(2, viewport.width(3))
    pygame.draw.circle(surface, palette.foreground, origin, max(3, viewport.width(6)))
    shot = math.floor(time / spec.cooldown)
    for k in range(shot, -1, -1):
        age = time - k * spec.cooldown
        if age > PREVIEW_SECONDS or advance_at(spec, age) >= spec.reach:
            break
        offset = projectile_offset(spec, age)
        # La Y del plano va hacia arriba; la de la pantalla, hacia abajo.
        point = origin + Vector2(offset.x, -offset.y) * scale
        if box.collidepoint(point):
            pygame.draw.circle(surface, palette.foreground, point, dot)


def _draw_player_preview(
    surface: pygame.Surface,
    box: pygame.Rect,
    player: PlayerSpec,
    viewport: Viewport,
    time: float,
    palette: Palette,
) -> None:
    """El jugador como quedaría: va y vuelve a su rapidez, con su radio, y tres puntos
    de experiencia caen hacia él tanto más rápido cuanto más carga tiene."""
    units = box.width / 400
    """Píxeles por unidad del plano dentro de la caja: la caja mide 400 de ancho."""
    span = 150.0
    period = 4 * span / player.speed
    phase = (time % period) / period
    # Una onda triangular: de −span a span y de vuelta, a rapidez constante.
    x = span * (4 * abs(phase - 0.5) - 1)
    center = Vector2(box.centerx + x * units, box.centery)
    pygame.draw.circle(surface, palette.foreground, center, player.radius * units)
    pull = abs(player.charge) / 14 * 0.5
    fall = (time * pull) % 1
    for corner in (box.topleft, box.topright, box.bottomleft):
        start = Vector2(corner)
        point = start + (center - start) * fall
        pygame.draw.circle(surface, palette.light.selection, point, max(2, units * 3))


def weapon_formula(spec: WeaponSpec) -> str:
    """La fórmula del arma, escrita desde sus términos (ADR 0029)."""
    advance = ""
    if spec.advance.coefficient:
        advance = ("v·τ", "v·t", "v·t²/2τ")[spec.advance.degree]
    waves = " + ".join(
        f"A{_sub(i)}·sin(k{_sub(i)}t + φ{_sub(i)})"
        for i in range(1, len(spec.harmonics) + 1)
    )
    if spec.frame == "polar":
        radius = " + ".join(term for term in (advance, waves) if term) or "0"
        return f"p(t) = p₀ + ({radius})·(cos Ωt, sin Ωt)"
    terms = [f"{advance}·û"] if advance else []
    if waves:
        terms.append(f"({waves})·n̂")
    return "p(t) = p₀ + " + " + ".join(terms) if terms else "p(t) = p₀"


def number(value: float) -> str:
    """Un número para leer: tres cifras, coma decimal y el signo menos de verdad."""
    if isinstance(value, int):
        text = str(value)
    elif abs(value) >= 100:
        text = f"{value:.0f}"
    else:
        text = f"{value:.3g}"
    return text.replace(".", ",").replace("-", "−")


def font(size: int) -> pygame.font.Font:
    """Tektur en `size` píxeles."""
    return _font(max(1, size))


@lru_cache(maxsize=FONT_SIZES)
def _font(size: int) -> pygame.font.Font:
    # Cada fuente lee su propio archivo en memoria: pygame lo sigue leyendo mientras
    # la fuente vive. Con tope: al arrastrar la ventana, cada alto pediría otra.
    return pygame.font.Font(io.BytesIO(_font_file()), size)


@cache
def _font_file() -> bytes:
    """El archivo de Tektur, leído del paquete con `importlib.resources`."""
    return resources.files("circlebh").joinpath("fonts/Tektur.ttf").read_bytes()


def _centered(
    surface: pygame.Surface,
    text: str,
    size: float,
    height: float,
    viewport: Viewport,
    color: pygame.Color,
) -> None:
    """Escribe `text` centrado a lo ancho, con su centro a `height` del alto. Si no cabe
    con un margen, lo achica."""
    rendered = font(viewport.width(size)).render(text, True, color)
    fit = surface.get_width() * TEXT_FIT
    if rendered.get_width() > fit:
        rendered = pygame.transform.smoothscale_by(rendered, fit / rendered.get_width())
    x = (surface.get_width() - rendered.get_width()) / 2
    y = surface.get_height() * height - rendered.get_height() / 2
    surface.blit(rendered, (x, y))


def _player_numbers(state: Loadout) -> dict[str, Json]:
    """Los números del jugador que una tarjeta puede cambiar, con sus usos."""
    numbers = dump(state.player)
    assert isinstance(numbers, dict)
    return numbers | {"rerolls": state.rerolls, "banishes": state.banishes}


def _diff(old: Json, new: Json) -> tuple[Change, ...]:
    """Los números que difieren entre `old` y `new`, por su ruta."""
    before = _flatten(old, "")
    changes = []
    for path, value in _flatten(new, "").items():
        was = before.get(path)
        numbers = (was, value)
        if was == value or not all(
            isinstance(n, int | float) and not isinstance(n, bool) for n in numbers
        ):
            continue
        assert isinstance(was, int | float) and isinstance(value, int | float)
        unit = UNITS.get(path, "")
        changes.append(
            Change(SYMBOLS.get(path, path), number(was) + unit, number(value) + unit)
        )
    return tuple(changes)


def _flatten(data: Json, prefix: str) -> dict[str, Json]:
    """`{"advance": {"coefficient": 300}}` → `{"advance.coefficient": 300}`."""
    if not isinstance(data, dict):
        return {prefix: data}
    flat: dict[str, Json] = {}
    for key, value in data.items():
        flat |= _flatten(value, f"{prefix}.{key}" if prefix else key)
    return flat


def _sub(n: int) -> str:
    """`n` con subíndices: 12 → ₁₂."""
    return "".join("₀₁₂₃₄₅₆₇₈₉"[int(d)] for d in str(n))
