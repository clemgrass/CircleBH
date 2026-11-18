---
estado: aceptado
fecha: 2026-11-18
---

# Licenciar el código con MIT

## Contexto y problema

El repo es público y busca servir de ejemplo para enseñar Pygame. Sin licencia, nadie puede reutilizar el código legalmente.

## Factores de decisión

- Que otros puedan reutilizar los ejemplos.
- Simplicidad.

## Opciones consideradas

- MIT
- Apache-2.0
- GPL-3.0
- Sin licencia

## Resultado de la decisión

Elegimos **MIT**: es corta y permisiva, y es la más común en portafolios y en código de ejemplo.

### Consecuencias

- Bueno: cualquiera puede usar el código citando el copyright.
- Malo: alguien puede publicar un derivado cerrado.
- Malo: es difícil de revertir para las copias que ya se distribuyeron.

### Confirmación

- El archivo `LICENSE` tiene el texto MIT y `pyproject.toml` declara `license = "MIT"`.

## Pros y contras de las opciones

### MIT
- Bueno: es simple y conocida.
- Malo: no protege contra derivados cerrados.

### Apache-2.0
- Bueno: tiene una cláusula explícita de patentes.
- Malo: es más larga y pide marcar los archivos cambiados.

### GPL-3.0
- Bueno: obliga a que los derivados sean libres.
- Malo: limita a quien quiera reutilizar los ejemplos.

### Sin licencia
- Bueno: no hay nada que decidir.
- Malo: legalmente, nadie puede reutilizar el código.

## Preguntas abiertas

- ¿Con qué nombre va el copyright de `LICENSE`? Se define al crear el archivo.
  - Respondida el 2026-11-18: `clemgrass`, el usuario de GitHub del autor.
