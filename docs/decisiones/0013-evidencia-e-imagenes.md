---
estado: aceptado
fecha: 2026-11-18
---

# Demostrar con capturas generadas y prueba manual, y permitir imágenes solo en docs/media

## Contexto y problema

Un cambio que se ve en pantalla necesita evidencia más allá de los tests. El juego no usa ningún archivo de imagen: la anti-meta del diseño prohíbe "cualquier archivo de imagen o sprite dibujado a mano". Al mismo tiempo, un README de portafolio sin imágenes no muestra el juego. Hay que decidir cómo se demuestra que algo funciona y qué imágenes, si alguna, pueden estar en el repo.

## Factores de decisión

- Evidencia real en cada cambio visible.
- Fidelidad a la idea del juego: todo se dibuja con código.
- Que un visitante vea el movimiento de las curvas sin descargar nada.

## Opciones consideradas

- README: PNG y GIF generados por el juego; solo PNG generados; adjuntos de GitHub sin archivos en el repo; o sin imágenes.
- Prueba manual: Claude escribe los pasos y el usuario el resultado; o el usuario escribe todo.

## Resultado de la decisión

- **Capturas como evidencia:**
  - `uv run poe capturas` corre `circlebh --demo --scenario <nombre> --seed N --capture t1,t2,…` sin ventana, con el driver de video `dummy` de SDL;
  - guarda los PNG en `.capturas/`, que está en `.gitignore`, y Claude los muestra en la sesión: el estado inicial, la interacción y el resultado;
  - los escenarios se definen en código, junto a la demo.
- **Imágenes del README:**
  - PNG y GIF generados solo por `uv run poe medios`, a partir de escenarios de la demo, y guardados en `docs/media/`;
  - Pillow 13.0.0 se suma como dependencia de desarrollo, para armar los GIF.
- **Control de imágenes:** una tarea de `poe check` falla si encuentra un archivo de imagen (png, jpg, jpeg, gif, bmp, tga, webp, svg, ico) fuera de `docs/media/`.
- **Prueba manual:**
  - en cada PR, Claude escribe los pasos y el usuario juega y escribe en simple qué vio. Después hace merge;
  - en un PR normal se prueba con `uv run circlebh`. En un release, además, se abre el zip del propio sistema.
- **Plantilla de PR:** Qué cambia, Por qué (`Cierra #N`), Verificación (los comandos y su salida) y Prueba manual.

### Consecuencias

- Bueno: cada cambio visible trae evidencia reproducible.
- Bueno: el README muestra el movimiento de cada arma.
- Bueno: la regla de imágenes sigue siendo una regla, con una sola excepción precisa.
- Malo: Pillow es una dependencia más.
- Malo: los GIF pesan en el repo.
- Malo: hay que regenerar los medios cuando cambia el aspecto del juego.

### Confirmación

- El control de imágenes corre en `poe check` y en la CI.
- `poe medios` regenera `docs/media/` desde el código.
- Pendiente de verificar al armar: el nombre exacto del driver `dummy`.

## Pros y contras de las opciones

### PNG y GIF generados
- Bueno: muestra el movimiento.
- Malo: suma Pillow y peso en el repo.

### Solo PNG generados
- Bueno: no suma dependencias.
- Malo: no muestra el movimiento.

### Adjuntos de GitHub
- Bueno: no hay imágenes en el repo.
- Malo: los enlaces dependen de GitHub y no se regeneran con un comando.

### Sin imágenes
- Bueno: es lo más fiel a la regla.
- Malo: un visitante no ve el juego.

### Claude los pasos, el usuario el resultado
- Bueno: el usuario no tiene que pensar los casos.
- Malo: puede probar solo lo que se le propuso.

### El usuario escribe todo
- Bueno: es más libre.
- Malo: es más trabajo en cada PR.

## Más información

- https://pyga.me/docs/ref/image.html (`image.save` guarda BMP, TGA, PNG y JPEG, no GIF; consultado el 2026-11-18)
- https://wiki.libsdl.org/SDL2/SDL_HINT_VIDEODRIVER (consultado el 2026-11-18)
- https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/writing-mathematical-expressions (fórmulas con MathJax; consultado el 2026-11-18)
