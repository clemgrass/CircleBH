---
estado: aceptado
fecha: 2026-11-18
---

# Usar pygame-ce 2.5.8 con Python 3.14

## Contexto y problema

El juego se hace en Python con Pygame, y eso ya estaba decidido. Faltaba elegir la variante de Pygame y la versión de Python. Existen dos distribuciones: el `pygame` original y `pygame-ce`, un fork de sus ex core developers.

## Factores de decisión

- Que tenga mantención activa y soporte para el Python actual.
- Que sirva como ejemplo vigente en un portafolio.
- Que todo el ecosistema (lint, tipos, empaquetado) funcione con la versión de Python elegida.

## Opciones consideradas

- pygame-ce 2.5.8
- pygame 2.6.1
- Python 3.14.10
- Python 3.15.2

## Resultado de la decisión

Elegimos **pygame-ce 2.5.8** con **Python 3.14.10**. El `pygame` original lleva más de dos años sin releases y no tiene wheels para Python 3.14. Python 3.14 tiene un año de correcciones, y 3.15 salió hace seis semanas.

### Consecuencias

- Bueno: hay releases cada 3 a 5 meses, wheels hasta Python 3.15 y tipos incluidos (`Typing :: Typed`).
- Bueno: el código se escribe igual, con `import pygame`.
- Malo: algunos tutoriales viejos no mencionan las funciones propias de pygame-ce.
- Malo: en un año, más o menos, habrá que subir a Python 3.15. Eso se hace con un ADR nuevo.

### Confirmación

- `.python-version` contiene `3.14.10`.
- `uv.lock` incluye `pygame-ce` 2.5.8 y no incluye `pygame`.
- La CI corre `poe check` con esa versión.

## Pros y contras de las opciones

### pygame-ce 2.5.8
- Bueno: está activo, con la última versión del 2026-08-09.
- Bueno: tiene wheels para Python 3.10 a 3.15, incluido Windows ARM.
- Malo: el nombre se conoce menos que "pygame".

### pygame 2.6.1
- Bueno: es el nombre más conocido.
- Malo: su última release es del 2024-09-29.
- Malo: sus wheels llegan solo hasta Python 3.13.

### Python 3.14.10
- Bueno: es madura y compatible con todas las herramientas elegidas.
- Malo: tiene menos vida por delante que 3.15.

### Python 3.15.2
- Bueno: es la más nueva.
- Malo: puede que el lint, los tipos o el empaquetado todavía no la soporten bien.

## Más información

- https://pypi.org/pypi/pygame-ce/json (consultado el 2026-11-18)
- https://pypi.org/pypi/pygame/json (consultado el 2026-11-18)
- https://www.python.org/api/v2/downloads/release/ (consultado el 2026-11-18)
- Pendiente de verificar al armar: que `pygame-ce` no puede convivir con `pygame` en el mismo entorno.
