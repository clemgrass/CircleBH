---
estado: aceptado
fecha: 2026-11-19
---

# Separar la configuración del juego del balance, en un solo JSON

Complementa el ADR 0004 sin reemplazarlo: el balance sigue como está.

## Contexto y problema

El ADR 0004 guarda en `balance.py` y `balance.json` cómo **son** las entidades: el jugador, los enemigos y las armas. Su objetivo es que un editor futuro pueda crear piezas nuevas.

Hay otro tipo de variable que no describe a ninguna entidad: la velocidad de la cámara, el área visible del plano (FOV), la zona muerta del control, las opciones de accesibilidad y las de depuración. Hoy no tienen lugar. Si quedan sueltas en el código, cambiarlas obliga a buscarlas, y más adelante no se pueden ofrecer en un menú de opciones.

El usuario pidió un solo archivo como fuente de verdad, tipo `.env`, donde cambiar una variable o agregar una nueva sea tocar ese archivo.

## Factores de decisión

- Una sola fuente de verdad para cada valor.
- Que agregar una variable sea simple.
- Que un error de tipeo se detecte al arrancar, con el nombre del campo.
- Que viaje dentro del ejecutable (ADR 0009).
- Que más adelante se puedan ofrecer variables al jugador.

## Opciones consideradas

- Un `settings.json` como fuente de verdad, con una dataclass que define campos y tipos
- Meter estas variables en el balance (ADR 0004)
- Constantes en un módulo Python, `settings.py` con valores
- Un `settings.toml`, que admite comentarios (no discutida)

## Resultado de la decisión

Elegimos **un `settings.json` como fuente de verdad**:

- Vive dentro del paquete, en `src/circlebh/settings.json`, y se lee con `importlib.resources`.
- Una dataclass congelada define los campos, sus tipos y, en un docstring, qué hace cada uno. El **valor** vive solo en el JSON.
- Al arrancar se valida contra la dataclass: si falta un campo, sobra uno o un tipo no calza, el juego no abre y el error nombra el campo (`camera.fov: se esperaba un número, llegó "ancho"`). La misma validación corre como test en `poe check`.
- Agregar una variable es un campo en la dataclass y su valor en el JSON.
- Qué va aquí y qué va al balance: si describe a una entidad (el jugador, un enemigo o un arma), va al balance. Si describe cómo se juega o se ve, va aquí.
- Lo que el jugador guarde por su cuenta, en su carpeta de usuario, queda para cuando exista un menú de opciones.

### Consecuencias

- Bueno: cada variable vive en un solo lugar, y cambiarla no exige tocar código.
- Bueno: un error en el archivo se ve al arrancar, con el nombre del campo, y no a mitad de la partida.
- Bueno: el futuro menú de opciones lee y escribe el mismo formato.
- Malo: JSON no admite comentarios. La explicación de cada variable va en el docstring de su campo, lejos del valor.
- Malo: son dos mecanismos de datos (el balance y la configuración), y hay que saber dónde va cada variable.

### Confirmación

- `src/circlebh/settings.json` existe y un test carga y valida el archivo real.
- Tests de la validación: un campo que falta, uno que sobra y uno con el tipo equivocado dan un error que nombra el campo.
- En la revisión se comprueba que las variables de cámara, controles, accesibilidad y depuración no estén escritas como constantes en el código.

## Pros y contras de las opciones

### `settings.json` con una dataclass
- Bueno: una sola verdad; `json` viene con Python y sirve para leer y escribir.
- Malo: sin comentarios en el archivo.

### Meterlas en el balance
- Bueno: un solo mecanismo.
- Malo: mezcla lo que el editor de entidades va a crear con cómo se juega, y arrastra la doble fuente del ADR 0004 a variables que no la necesitan.

### Constantes en `settings.py`
- Bueno: lo más simple, con comentarios al lado del valor.
- Malo: cambiar un valor es tocar código, y no se puede ofrecer al jugador sin otro formato.

### `settings.toml` (no discutida)
- Bueno: admite comentarios junto al valor.
- Malo: `tomllib` solo lee; escribirlo desde un menú de opciones exige una dependencia más.
