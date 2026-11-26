"""Tests de la mezcla entre el tema y la música de la mano (spec de la 0.3.0, decisión
16, enfoque A).

El tema de prueba es una rampa: la muestra `i` del canal izquierdo vale `i` (módulo
`RAMPA`), y la del derecho, `−i`. Así se ve qué se leyó y en qué orden.
"""

import itertools
from array import array
from collections import deque

import pytest

from circlebh.audio.deck import FADE_IN, FADE_OUT, PREFILL, Deck
from circlebh.audio.harmony import Variation
from circlebh.audio.sequencer import SAMPLES_PER_STEP
from circlebh.world.clock import STEP, slowdown_rate, slowdown_steps

RAMPA = 32000
ARMONIA = (Variation(transpose=0, first_chord=0), 0)
ENTRA = round(FADE_IN / STEP)
SALE = round(FADE_OUT / STEP)


def rampa(desde: int, cuantas: int) -> bytes:
    """`cuantas` muestras estéreo de la rampa, desde la muestra `desde`."""
    out = array("h")
    for i in range(desde, desde + cuantas):
        out += array("h", [i % RAMPA, -(i % RAMPA)])
    return out.tobytes()


def salida(deck: Deck) -> array[int]:
    """Todo lo que la mezcla entregó, como muestras intercaladas izquierda-derecha."""
    out = array("h")
    out.frombytes(b"".join(deck.ready))
    deck.ready.clear()
    return out


def tocar(deck: Deck, pasos: int, rate: float = 1.0, *, mano: bool = False) -> None:
    for _ in range(pasos):
        deck.step(rate, mano, ARMONIA)


def test_sin_mano_deja_pasar_el_tema() -> None:
    deck = Deck()
    deck.feed(deque([rampa(0, PREFILL + 100 * SAMPLES_PER_STEP)]))
    tocar(deck, 80)
    out = salida(deck)
    assert len(out) > 0
    assert out == array("h", rampa(0, len(out) // 2))


def test_despues_del_frenado_el_tema_vuelve_a_salir_tal_cual() -> None:
    # A media velocidad la lectura queda entre dos muestras. Al volver a 1, el tema
    # tiene que salir otra vez muestra por muestra, sin interpolar.
    deck = Deck()
    deck.feed(deque([rampa(0, PREFILL + 100 * SAMPLES_PER_STEP)]))
    tocar(deck, 4)
    tocar(deck, 3, 0.5)
    tocar(deck, 9)
    izquierda = list(salida(deck)[::2])[-SAMPLES_PER_STEP:]
    assert all(b - a == 1 for a, b in itertools.pairwise(izquierda))


def test_con_la_mano_no_gasta_el_tema() -> None:
    deck = Deck()
    deck.feed(deque([rampa(0, PREFILL + 100 * SAMPLES_PER_STEP)]))
    tocar(deck, 10)
    antes = deck.buffered
    tocar(deck, 60, 0.0, mano=True)
    assert deck.buffered == antes
    assert deck.fade == 1


def test_vuelve_desde_donde_quedo() -> None:
    deck = Deck()
    deck.feed(deque([rampa(0, PREFILL + 100 * SAMPLES_PER_STEP)]))
    tocar(deck, 8)
    tocar(deck, ENTRA, 0.0, mano=True)
    tocar(deck, SALE + 2)
    out = salida(deck)
    # Al terminar el cruce sale solo el tema: la última muestra es la siguiente a todo
    # lo que se leyó, sin saltarse lo que quedó en pausa.
    leidas = (8 + SALE + 2) * SAMPLES_PER_STEP
    assert len(out) == 2 * (8 + ENTRA + SALE + 2) * SAMPLES_PER_STEP
    assert out[-2] == (leidas - 1) % RAMPA
    assert out[-1] == -((leidas - 1) % RAMPA)


def test_cruce_dura_lo_que_dice() -> None:
    deck = Deck()
    tocar(deck, ENTRA - 1, 0.0, mano=True)
    assert 0 < deck.fade < 1
    tocar(deck, 1, 0.0, mano=True)
    assert deck.fade == 1
    tocar(deck, SALE - 1)
    assert 0 < deck.fade < 1
    tocar(deck, 1)
    assert deck.fade == 0


def test_mano_abre_a_medio_cruce() -> None:
    # Borde: el cruce da la vuelta desde donde iba, sin saltar.
    deck = Deck()
    tocar(deck, ENTRA, 0.0, mano=True)
    tocar(deck, 10)
    medio = deck.fade
    assert 0 < medio < 1
    tocar(deck, 1, 0.0, mano=True)
    assert deck.fade == pytest.approx(medio + STEP / FADE_IN)


def test_con_la_mano_suena_su_musica() -> None:
    deck = Deck()
    tocar(deck, ENTRA + 16, 0.0, mano=True)
    out = salida(deck)
    assert any(out)


def test_frenado_gasta_lo_producido() -> None:
    # Borde: en el frenado, el tema llega a la velocidad del mundo y se lee igual.
    n = 12
    deck = Deck()
    deck.feed(deque([rampa(0, PREFILL)]))
    producidas = PREFILL
    tocar(deck, 1)
    antes = deck.buffered
    dados = 0
    for j in range(1, 2 * n + 1):
        while slowdown_steps(j, n) > dados:
            deck.feed(deque([rampa(producidas, SAMPLES_PER_STEP)]))
            producidas += SAMPLES_PER_STEP
            dados += 1
        deck.step(slowdown_rate(j, n), True, ARMONIA)
    leidas = antes + n * SAMPLES_PER_STEP - deck.buffered
    assert abs(leidas - n * SAMPLES_PER_STEP) < SAMPLES_PER_STEP


def test_sin_tema_sale_silencio() -> None:
    # Negativo: sin bloques no falla, y lo que sale es silencio.
    deck = Deck()
    tocar(deck, 16)
    out = salida(deck)
    assert len(out) == 2 * 16 * SAMPLES_PER_STEP
    assert not any(out)


def test_tema_que_se_acaba_no_repite_muestras() -> None:
    # Negativo: si el tema no alcanzó a llegar, sale silencio, no la última muestra.
    deck = Deck()
    deck.feed(deque([rampa(1, PREFILL)]))
    tocar(deck, PREFILL // SAMPLES_PER_STEP + 16)
    izquierda = list(salida(deck)[::2])
    sonido = [x for x in izquierda if x]
    assert sonido == sorted(set(sonido))
    assert izquierda[-1] == 0
