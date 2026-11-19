---
estado: propuesto
fecha: 2026-11-19
---

# Leer el control con `pygame._sdl2.controller`

## Contexto y problema

La 0.1.0 se juega con un control de PlayStation, con el stick izquierdo y la cruceta, y el control se puede conectar o desconectar con el juego abierto (spec de la 0.1.0, decisión 6). pygame-ce 2.5.8 trae dos APIs para leerlo:

- `pygame.joystick`: entrega índices crudos de ejes, botones y hats.
- `pygame._sdl2.controller`: usa la API GameController de SDL, que traduce cada control conocido a un layout con nombre (`leftx`, `dpup`).

Los índices crudos cambian según el driver, aunque el control y el sistema sean los mismos. La documentación de `pygame.joystick` muestra el PS4 con la cruceta en los botones 11–14. El mismo PS4, conectado por Bluetooth en Linux, trae la cruceta como hat, y ahí los botones 11 y 12 son apretar los sticks (ver "Más información").

## Factores de decisión

- Que el stick y la cruceta funcionen igual en Linux, Windows y macOS, aunque solo podemos probar en Linux.
- Que conectar o desconectar el control no cierre el juego.
- Una sola forma de leer el control, simple de mantener.
- No sumar dependencias.

## Opciones consideradas

- `pygame._sdl2.controller`
- `pygame.joystick`, con los índices crudos
- `controller` para los controles que SDL reconoce y `joystick` para el resto

## Resultado de la decisión

Elegimos **`pygame._sdl2.controller`**:

- El stick izquierdo se lee con `CONTROLLER_AXIS_LEFTX` y `CONTROLLER_AXIS_LEFTY`, y la cruceta con `CONTROLLER_BUTTON_DPAD_*`.
- Los ejes llegan como enteros de −32768 a 32767. Una función pura de `controls.py` los pasa a −1..1, y ahí se aplica la zona muerta.
- La reconexión en caliente usa `CONTROLLERDEVICEADDED` (que trae `device_index`) y `CONTROLLERDEVICEREMOVED`.
- `pygame._sdl2.controller` se usa en un solo módulo de `scenes/`. Si su API cambia, se cambia solo ahí.
- Un control que SDL no reconoce no mueve al jugador. El teclado sigue funcionando.

### Consecuencias

- Bueno: el layout con nombre viene de la base de datos de controles de SDL. No escribimos tablas de índices por plataforma ni por driver.
- Bueno: la cruceta llega como cuatro botones, sea hat o botones en el driver.
- Malo: el índice de la documentación de pygame-ce pone el módulo en "Experimental modules" y pide no depender de él. Su API podría cambiar en otra versión. Lo acota que `uv.lock` fija la versión, que las dependencias se actualizan a mano al empezar cada milestone (ADR 0002) y que se usa en un solo módulo.
- Malo: un control que SDL no conoce no funciona, aunque `pygame.joystick` sí lo vería.

### Confirmación

- `grep -rn "_sdl2" src/` muestra un solo módulo, en `scenes/`.
- `controls.py` tiene tests de la conversión del eje, la zona muerta y la Y invertida.
- Prueba manual antes del PR de cada versión: el stick y la cruceta mueven al jugador, y desconectar y reconectar el control no cierra el juego.

## Pros y contras de las opciones

### `pygame._sdl2.controller`
- Bueno: el mismo layout con nombre en todos los sistemas y drivers.
- Malo: es un módulo experimental en pygame-ce.

### `pygame.joystick`, con los índices crudos
- Bueno: la API es estable y documentada.
- Malo: hay que leer la cruceta como hat o como botones según el driver, y los botones 11–14 de un layout son apretar los sticks en el otro. No podemos verificar Windows ni macOS.

### `controller` y `joystick` de respaldo
- Bueno: cubre también los controles que SDL no reconoce.
- Malo: son dos caminos que mantener, más de lo que pide la 0.1.0.

## Más información

- https://pyga.me/docs/ (consultado el 2026-11-19; documentación de la v2.5.9): el índice pone `_sdl2.controller` en "Experimental modules" y dice: "Experimental modules are work in progress, this is why you should refrain from relying on any features provided by these modules."
- https://pyga.me/docs/ref/sdl2_controller.html (consultado el 2026-11-19): "Joysticks can return a value between -32768 and 32767."
- https://raw.githubusercontent.com/pygame-community/pygame-ce/2.5.8/docs/reST/ref/sdl2_controller.rst (consultado el 2026-11-19): la página de la versión 2.5.8 no trae advertencias propias de inestabilidad.
- https://pyga.me/docs/ref/joystick.html (consultado el 2026-11-19): la tabla del PS4 con pygame 2 pone la cruceta en los botones 11–14, y dice que los mapeos "differ between pygame 1 and pygame 2".
- Diagnóstico con pygame-ce 2.5.8 y SDL 2.32.10, con un control PS4 por Bluetooth en Linux, el 2026-11-19:

  ```
  0 'Wireless Controller' … ejes 6 botones 13 hats 1 is_controller: True
  controller name: 'PS4 Controller'
  mapping: {'dpup': 'h0.1', 'dpdown': 'h0.4', 'dpleft': 'h0.8', 'dpright': 'h0.2',
            'leftx': 'a0', 'lefty': 'a1', 'rightx': 'a3', 'righty': 'a4',
            'leftstick': 'b11', 'rightstick': 'b12', …}
  ControllerDeviceAdded {'device_index': 0, 'guid': '05009b514c050000c405000000810000'}
  leftx, lefty en reposo: -2956 -386
  ```

  Con el stick suelto, `leftx` marca −2956, cerca del 9 % del rango. La zona muerta de 0,2 lo cubre.
- Diagnóstico al apagar el mismo control con el juego abierto, el 2026-11-19:

  ```
  ControllerDeviceRemoved {'instance_id': 0}
  attached tras quitarlo: False
  get_axis tras quitarlo: -2956
  JoyDeviceRemoved {'instance_id': 0}
  ```

  Leer un control quitado no lanza error: devuelve el último valor. Por eso, al llegar `CONTROLLERDEVICEREMOVED`, el control se suelta. Si no, un stick inclinado al desconectar seguiría moviendo al jugador. El alta trae `device_index` y la baja trae `instance_id`, así que cada control se guarda con el `instance_id` de su joystick.
- No verificado: cómo se ve el mismo control en Windows y macOS, y cómo se ve conectado por USB.
