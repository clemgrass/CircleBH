---
estado: aceptado
fecha: 2026-11-18
---

# Mantener el balance en balance.py y balance.json, coordinados

## Contexto y problema

Los números de equilibrio deben vivir en un lugar fácil de cambiar. Además, enemigos y armas se definen por parámetros y no con código escrito a mano para cada uno, para que un editor futuro pueda armarlos. Hay que decidir el formato y dónde vive cada cosa.

## Factores de decisión

- Que sea fácil de leer y de cambiar a mano.
- Que todo se pueda serializar, así la puerta al editor queda garantizada en el código.
- Que una diferencia nunca se pise en silencio.

## Opciones consideradas

- Solo `balance.py`, con dataclasses
- Un archivo TOML
- Un archivo JSON
- `balance.py` y un JSON generado en una sola dirección (manda Python)
- `balance.py` y `balance.json` coordinados en las dos direcciones
- Solo un test de ida y vuelta, sin JSON en el repo

## Resultado de la decisión

Elegimos **`balance.py` (dataclasses) y `balance.json`, coordinados**.

- Los dos archivos se pueden editar y ninguno manda: deben calzar siempre.
- Un chequeo de coherencia corre en tres lugares: como test en la CI, como comando suelto y al arrancar el juego. Si hay diferencias, nombra el campo exacto, por ejemplo `enemies.hexagon.speed: balance.py=3.0, balance.json=2.5`.
- La diferencia se corrige a mano antes de jugar o de armar un build. Para eso hay dos comandos, cada uno con su dirección: exportar (Python → JSON) e importar (JSON → Python).
- `balance.json` vive dentro del paquete y se lee con `importlib.resources`.

### Consecuencias

- Bueno: si alguien mete una función o una `lambda` en una definición, el export falla. Así todo queda como dato puro.
- Bueno: el editor futuro puede escribir JSON sin tocar Python.
- Bueno: nunca se pisa un cambio sin que alguien lo vea.
- Malo: un cambio se hace en dos lugares, o se hace en uno y se corre un comando.
- Malo: importar de JSON a Python significa generar código, y es la pieza más grande.
- Malo: el ejecutable tiene que incluir el JSON, o el juego no arranca.

### Confirmación

- El test de coherencia corre en `poe check`.
- El smoke del ejecutable en el release arranca el juego, y con eso corre el chequeo.

## Pros y contras de las opciones

### Solo `balance.py`
- Bueno: tiene tipos, autocompletado y no necesita parser.
- Malo: el editor tendría que migrar después a un archivo de datos.

### TOML
- Bueno: separa los datos del código y se lee con `tomllib`.
- Malo: hay que escribir la carga y la validación, y `tomllib` no escribe archivos.

### JSON
- Bueno: la librería estándar lo lee y lo escribe.
- Malo: no admite comentarios y también necesita validación.

### Python que manda y JSON generado
- Bueno: hay una sola dirección y nada es ambiguo.
- Malo: el editor tendría que invertir la dirección con otra decisión.

### Coordinados en las dos direcciones
- Bueno: se puede editar cualquiera de los dos, y el chequeo impide que se descuadren.
- Malo: son dos comandos y el import necesita generar código.

### Solo un test de ida y vuelta
- Bueno: es lo mínimo y no hay archivo que mantener.
- Malo: no hay un JSON a la vista para el editor.

## Preguntas abiertas

- ¿El import de JSON a Python va en el MVP o cuando llegue el editor? Se decide al planificar las tareas.
  - Respondida el 2026-11-19: va desde el inicio, en la 0.1.0. El usuario prefiere hacerla ahora porque es más fácil que agregarla después. La importación reescribe los datos, no las clases (spec `docs/specs/2026-11-19-version-0-1-0.md`).
